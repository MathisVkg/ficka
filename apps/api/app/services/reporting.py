"""Read-only reporting: database aggregates, date-only boundaries, EUR only."""

import calendar
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal, localcontext

from fastapi import HTTPException
from sqlalchemy import Date, DateTime, Integer, case, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models import Category, Entry

ZERO = Decimal("0.00")


def month_start(day: date) -> date:
    return day.replace(day=1)


def month_end(day: date) -> date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def next_month(day: date) -> date:
    return date(day.year + (day.month == 12), day.month % 12 + 1, 1)


def resolve_period(start: date | None, end: date | None) -> tuple[date, date]:
    if (start is None) != (end is None):
        raise HTTPException(422, "Provide both date_from and date_to")
    start, end = (
        (month_start(date.today()), month_end(date.today())) if start is None else (start, end)
    )
    if start.year < 1900 or end.year > 2100:
        raise HTTPException(422, "Reporting dates must be between 1900 and 2100")
    if start > end:
        raise HTTPException(422, "date_from must be on or before date_to")
    if (end - start).days > 1830:
        raise HTTPException(422, "Choose a report range of at most 1,831 calendar days")
    return start, end


def add(values) -> Decimal:
    # Enough precision even for BIGINT row counts × the model's NUMERIC(14,2).
    with localcontext() as context:
        context.prec = 50
        return sum(values, ZERO)


def difference(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 50
        return left - right


def sum_if(condition, column=Entry.amount):
    return func.coalesce(func.sum(case((condition, column), else_=ZERO)), ZERO)


def count_if(condition):
    return func.count(case((condition, Entry.id)))


def period_meta(start, end, **values):
    return {"date_from": start, "date_to": end, **values}


def summary(session: Session, start: date, end: date):
    cash_date = Entry.payment_date.between(start, end)
    vat_date = Entry.entry_date.between(start, end)
    eur = Entry.currency == "EUR"
    actual = eur & cash_date & (Entry.status == "paid")
    expected = eur & cash_date & (Entry.status == "pending")
    vat = eur & vat_date
    incoming = Entry.type == "income"
    outgoing = Entry.type == "expense"
    row = session.execute(
        select(
            sum_if(actual & incoming).label("income"),
            sum_if(actual & outgoing).label("expenses"),
            count_if(actual).label("actual_count"),
            sum_if(expected & incoming).label("expected_income"),
            sum_if(expected & outgoing).label("expected_expenses"),
            count_if(expected).label("expected_count"),
            sum_if(vat & incoming, Entry.vat_amount).label("output_vat"),
            sum_if(vat & outgoing, Entry.vat_amount).label("input_vat"),
            count_if(vat).label("vat_count"),
            count_if(~eur & cash_date).label("excluded_cash"),
            count_if(~eur & vat_date).label("excluded_vat"),
        ).where(
            Entry.deleted_at.is_(None),
            Entry.status.in_(["paid", "pending"]),
            or_(cash_date, vat_date),
        )
    ).one()
    return period_meta(
        start,
        end,
        non_eur_excluded_count=row.excluded_cash,
        actual={
            "income": row.income,
            "expenses": row.expenses,
            "net": difference(row.income, row.expenses),
            "entry_count": row.actual_count,
        },
        expected={
            "income": row.expected_income,
            "expenses": row.expected_expenses,
            "net": difference(row.expected_income, row.expected_expenses),
            "entry_count": row.expected_count,
        },
        vat={
            "output": row.output_vat,
            "input": row.input_vat,
            "difference": difference(row.output_vat, row.input_vat),
            "entry_count": row.vat_count,
            "non_eur_excluded_count": row.excluded_vat,
        },
    )


def cash_flow(session: Session, start: date, end: date, grouping: str, basis: str):
    # Explicit timestamp WITHOUT time zone: these are stored calendar dates, not instants.
    bucket = cast(func.date_trunc(grouping, cast(Entry.payment_date, DateTime())), Date)
    rows = session.execute(
        select(
            bucket.label("bucket"),
            Entry.type,
            Entry.currency,
            func.sum(Entry.amount).label("amount"),
            func.count().label("entry_count"),
        )
        .where(
            Entry.deleted_at.is_(None),
            Entry.status == ("paid" if basis == "actual" else "pending"),
            Entry.payment_date.between(start, end),
        )
        .group_by(bucket, Entry.type, Entry.currency)
    ).all()
    values = {}
    excluded = 0
    for row in rows:
        if row.currency != "EUR":
            excluded += row.entry_count
            continue
        record = values.setdefault(row.bucket, {"income": ZERO, "expenses": ZERO, "entry_count": 0})
        record["income" if row.type == "income" else "expenses"] = row.amount
        record["entry_count"] += row.entry_count
    cursor = month_start(start) if grouping == "month" else start - timedelta(days=start.weekday())
    items = []
    while cursor <= end:
        following = next_month(cursor) if grouping == "month" else cursor + timedelta(days=7)
        record = values.get(cursor, {"income": ZERO, "expenses": ZERO, "entry_count": 0})
        items.append(
            {
                "bucket_start": cursor,
                "date_from": max(start, cursor),
                "date_to": min(end, following - timedelta(days=1)),
                **record,
                "net": difference(record["income"], record["expenses"]),
            }
        )
        cursor = following
    return period_meta(
        start,
        end,
        grouping=grouping,
        basis=basis,
        items=items,
        entry_count=sum(item["entry_count"] for item in items),
        non_eur_excluded_count=excluded,
    )


def percentages(amounts: list[Decimal]) -> list[Decimal]:
    total = add(amounts)
    if not total:
        return [ZERO for _ in amounts]
    with localcontext() as context:
        context.prec = 50
        exact = [amount * Decimal(10000) / total for amount in amounts]
        points = [int(value.to_integral_value(rounding=ROUND_DOWN)) for value in exact]
        remaining = 10000 - sum(points)
        order = sorted(range(len(amounts)), key=lambda i: (-(exact[i] - points[i]), i))
        for index in order[:remaining]:
            points[index] += 1
        return [Decimal(value) / Decimal(100) for value in points]


def categories(session: Session, start: date, end: date, kind: str):
    rows = session.execute(
        select(
            Entry.category_id,
            Category.name,
            Category.color,
            Category.active,
            Entry.currency,
            func.sum(Entry.amount).label("amount"),
            func.count().label("entry_count"),
        )
        .outerjoin(Category, Entry.category_id == Category.id)
        .where(
            Entry.deleted_at.is_(None),
            Entry.status == "paid",
            Entry.type == kind,
            Entry.payment_date.between(start, end),
        )
        .group_by(Entry.category_id, Category.name, Category.color, Category.active, Entry.currency)
    )
    included, excluded = [], 0
    for row in rows:
        if row.currency != "EUR":
            excluded += row.entry_count
        else:
            included.append(
                {
                    "id": row.category_id,
                    "name": row.name or "Uncategorized",
                    "color": row.color,
                    "active": row.active,
                    "amount": row.amount,
                    "entry_count": row.entry_count,
                }
            )
    included.sort(
        key=lambda item: (item["amount"].copy_negate(), item["name"].casefold(), str(item["id"]))
    )
    for item, percentage in zip(
        included, percentages([item["amount"] for item in included]), strict=True
    ):
        item["percentage"] = percentage
    return period_meta(
        start,
        end,
        type=kind,
        total=add(item["amount"] for item in included),
        entry_count=sum(item["entry_count"] for item in included),
        items=included,
        non_eur_excluded_count=excluded,
    )


def pending(session: Session, start, end, scope, as_of, kind, page, page_size):
    conditions = [Entry.deleted_at.is_(None), Entry.status == "pending"]
    if scope == "period":
        conditions.append(Entry.payment_date.between(start, end))
    if kind:
        conditions.append(Entry.type == kind)
    eur = Entry.currency == "EUR"
    row = session.execute(
        select(
            sum_if(eur & (Entry.type == "income")).label("income"),
            sum_if(eur & (Entry.type == "expense")).label("expenses"),
            count_if(eur).label("total"),
            count_if(eur & (Entry.payment_date < as_of)).label("overdue"),
            count_if(~eur).label("excluded"),
        ).where(*conditions)
    ).one()
    entries = session.execute(
        select(Entry.id, Entry.type, Entry.title, Entry.amount, Entry.payment_date)
        .where(*conditions, eur)
        .order_by(Entry.payment_date, Entry.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "scope": scope,
        "date_from": start,
        "date_to": end,
        "as_of": as_of,
        "income": row.income,
        "expenses": row.expenses,
        "net": difference(row.income, row.expenses),
        "total": row.total,
        "overdue_count": row.overdue,
        "non_eur_excluded_count": row.excluded,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": e.id,
                "type": e.type,
                "title": e.title,
                "amount": e.amount,
                "payment_date": e.payment_date,
                "overdue": e.payment_date < as_of,
            }
            for e in entries
        ],
    }


def vat(session: Session, year: int):
    start, end = date(year, 1, 1), date(year, 12, 31)
    quarter = cast(func.extract("quarter", Entry.entry_date), Integer)
    rows = session.execute(
        select(
            quarter.label("quarter"),
            Entry.type,
            Entry.currency,
            func.sum(Entry.vat_amount).label("vat"),
            func.count().label("entry_count"),
        )
        .where(
            Entry.deleted_at.is_(None),
            Entry.status.in_(["pending", "paid"]),
            Entry.entry_date.between(start, end),
        )
        .group_by(quarter, Entry.type, Entry.currency)
    ).all()
    values, excluded = {}, 0
    for row in rows:
        if row.currency != "EUR":
            excluded += row.entry_count
            continue
        record = values.setdefault(row.quarter, {"output": ZERO, "input": ZERO, "entry_count": 0})
        record["output" if row.type == "income" else "input"] = row.vat
        record["entry_count"] += row.entry_count
    quarters = []
    for number in range(1, 5):
        first = date(year, (number - 1) * 3 + 1, 1)
        last = month_end(date(year, number * 3, 1))
        record = values.get(number, {"output": ZERO, "input": ZERO, "entry_count": 0})
        quarters.append(
            {
                "quarter": number,
                "date_from": first,
                "date_to": last,
                **record,
                "difference": difference(record["output"], record["input"]),
            }
        )
    output, input_vat = add(q["output"] for q in quarters), add(q["input"] for q in quarters)
    return period_meta(
        start,
        end,
        year=year,
        output=output,
        input=input_vat,
        difference=difference(output, input_vat),
        quarters=quarters,
        entry_count=sum(q["entry_count"] for q in quarters),
        non_eur_excluded_count=excluded,
    )
