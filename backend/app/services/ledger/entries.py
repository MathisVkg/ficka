"""Entries (income and expenses), their lines and payments.

Rules (docs/database.md, "Rules enforced by the service layer"):
- amounts live on the lines; totals are recomputed from them on every write
- a line's rate must be valid on the invoice date for the company's country (or NULL)
- `source` is set on creation and never changes
- payment status is derived (see payment_status.py), never stored
Every function takes the company (or its id) first; other companies' rows are NotFound.
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import case, delete, func, or_
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from app.errors import Conflict, NotFound, ValidationFailed
from app.models import (
    Category,
    Company,
    Counterparty,
    Direction,
    Entry,
    EntryLine,
    EntrySource,
    EntryStatus,
    Payment,
    PaymentSource,
)
from app.models.base import utc_now
from app.services import identifiers, vat
from app.services.ledger.payment_status import (
    PaymentStatus,
    paid_cents_expr,
    payment_status_expr,
)

MAX_LINES = 200


def format_cents(cents: int) -> str:
    """1 512,50 € (for messages; the frontend formats amounts itself)."""
    sign = "-" if cents < 0 else ""
    euros, rest = divmod(abs(cents), 100)
    grouped = f"{euros:,}".replace(",", " ")
    return f"{sign}{grouped},{rest:02d} €"


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


# --- Input ---------------------------------------------------------------------------------


@dataclass
class LineInput:
    description: str | None = None
    net_cents: int | None = None
    gross_cents: int | None = None
    vat_rate_bp: int | None = None
    vat_cents: int | None = None
    vat_manual: bool = False


@dataclass
class EntryInput:
    direction: Direction
    invoice_date: date
    lines: list[LineInput]
    due_date: date | None = None
    counterparty_id: int | None = None
    category_id: int | None = None
    description: str | None = None
    invoice_number: str | None = None
    structured_reference: str | None = None
    amounts_include_vat: bool = False
    document_location: str | None = None


@dataclass(frozen=True)
class EntryWarning:
    code: str
    message: str


@dataclass
class _Prepared:
    header: dict
    lines: list[tuple[LineInput, vat.LineAmounts]]
    net: int = 0
    vat: int = 0
    gross: int = 0


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def _prepare(session: Session, company: Company, data: EntryInput) -> _Prepared:
    """Validate everything and compute the lines; raise one ValidationFailed with all fields."""
    assert company.id is not None
    errors: dict[str, str] = {}

    if data.due_date is not None and data.due_date < data.invoice_date:
        errors["due_date"] = "The due date can't be before the invoice date."

    if data.counterparty_id is not None:
        counterparty = session.get(Counterparty, data.counterparty_id)
        if counterparty is None or counterparty.company_id != company.id:
            errors["counterparty_id"] = "Choose one of your counterparties."

    if data.category_id is not None:
        category = session.get(Category, data.category_id)
        if category is None or category.company_id != company.id:
            errors["category_id"] = "Choose one of your categories."
        elif category.direction != data.direction:
            kind = "an income" if data.direction == Direction.INCOME else "an expense"
            errors["category_id"] = f"Choose {kind} category."

    structured_reference = None
    if _clean(data.structured_reference):
        try:
            structured_reference = identifiers.normalize_structured_reference(
                data.structured_reference or ""
            )
        except identifiers.IdentifierError as exc:
            errors["structured_reference"] = str(exc)

    if not data.lines:
        errors["lines"] = "Add at least one line."
    elif len(data.lines) > MAX_LINES:
        errors["lines"] = f"An entry can have at most {MAX_LINES} lines."

    valid_rates = vat.valid_rate_set(session, company.country_code, data.invoice_date)
    amount_key = "gross_cents" if data.amounts_include_vat else "net_cents"
    lines: list[tuple[LineInput, vat.LineAmounts]] = []
    for index, line in enumerate(data.lines[:MAX_LINES]):
        prefix = f"lines.{index}"
        amount = line.gross_cents if data.amounts_include_vat else line.net_cents
        if amount is None:
            errors[f"{prefix}.{amount_key}"] = "Enter an amount."
            continue
        if line.vat_rate_bp is not None and line.vat_rate_bp not in valid_rates:
            errors[f"{prefix}.vat_rate_bp"] = (
                f"This VAT rate isn't valid on {format_date(data.invoice_date)}."
            )
            continue
        try:
            amounts = vat.compute_line(
                amount,
                line.vat_rate_bp,
                amounts_include_vat=data.amounts_include_vat,
                vat_manual=line.vat_manual,
                vat_cents=line.vat_cents,
            )
        except vat.VatError as exc:
            errors[f"{prefix}.{exc.field}"] = exc.message
            continue
        lines.append((line, amounts))

    if errors:
        raise ValidationFailed("Some fields need your attention.", fields=errors)

    prepared = _Prepared(
        header={
            "direction": data.direction,
            "invoice_date": data.invoice_date,
            "due_date": data.due_date,
            "counterparty_id": data.counterparty_id,
            "category_id": data.category_id,
            "description": _clean(data.description),
            "invoice_number": _clean(data.invoice_number),
            "structured_reference": structured_reference,
            "amounts_include_vat": data.amounts_include_vat,
            "document_location": _clean(data.document_location),
        },
        lines=lines,
    )
    for _line, amounts in lines:
        prepared.net += amounts.net_cents
        prepared.vat += amounts.vat_cents
        prepared.gross += amounts.gross_cents
    if prepared.gross > vat.MAX_AMOUNT_CENTS:
        raise ValidationFailed(
            "The total is too large.", fields={"lines": "The total of the lines is too large."}
        )
    return prepared


def _write_lines(session: Session, entry_id: int, prepared: _Prepared) -> None:
    for position, (line, amounts) in enumerate(prepared.lines):
        session.add(
            EntryLine(
                entry_id=entry_id,
                position=position,
                description=_clean(line.description),
                net_cents=amounts.net_cents,
                vat_rate_bp=line.vat_rate_bp,
                vat_cents=amounts.vat_cents,
                vat_manual=line.vat_manual and line.vat_rate_bp is not None,
            )
        )


def _apply_header(entry: Entry, prepared: _Prepared) -> None:
    for key, value in prepared.header.items():
        setattr(entry, key, value)
    entry.total_net_cents = prepared.net
    entry.total_vat_cents = prepared.vat
    entry.total_gross_cents = prepared.gross


# --- Reading -------------------------------------------------------------------------------


def get_entry(session: Session, company_id: int, entry_id: int) -> Entry:
    entry = session.get(Entry, entry_id)
    if entry is None or entry.company_id != company_id:
        raise NotFound("This entry doesn't exist.")
    return entry


def paid_cents_of(session: Session, entry_id: int) -> int:
    return session.exec(
        select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(Payment.entry_id == entry_id)
    ).one()


@dataclass
class EntryDetail:
    entry: Entry
    lines: list[EntryLine]
    payments: list[Payment]
    paid_cents: int
    payment_status: PaymentStatus
    counterparty_name: str | None
    category_name: str | None

    @property
    def remaining_cents(self) -> int:
        return max(0, self.entry.total_gross_cents - self.paid_cents)


def entry_detail(session: Session, company_id: int, entry_id: int, today: date) -> EntryDetail:
    row = session.exec(
        select(
            Entry, paid_cents_expr(), payment_status_expr(today), Counterparty.name, Category.name
        )
        .outerjoin(Counterparty, col(Counterparty.id) == Entry.counterparty_id)
        .outerjoin(Category, col(Category.id) == Entry.category_id)
        .where(Entry.id == entry_id, Entry.company_id == company_id)
    ).first()
    if row is None:
        raise NotFound("This entry doesn't exist.")
    entry, paid, status, counterparty_name, category_name = row
    lines = session.exec(
        select(EntryLine)
        .where(EntryLine.entry_id == entry_id)
        .order_by(col(EntryLine.position), col(EntryLine.id))
    ).all()
    payments = session.exec(
        select(Payment)
        .where(Payment.entry_id == entry_id)
        .order_by(col(Payment.paid_on), col(Payment.id))
    ).all()
    return EntryDetail(
        entry=entry,
        lines=list(lines),
        payments=list(payments),
        paid_cents=paid,
        payment_status=PaymentStatus(status),
        counterparty_name=counterparty_name,
        category_name=category_name,
    )


def warnings_for(session: Session, entry: Entry) -> list[EntryWarning]:
    found: list[EntryWarning] = []
    if entry.counterparty_id is not None and entry.invoice_number:
        duplicate = session.exec(
            select(Entry.id).where(
                Entry.company_id == entry.company_id,
                Entry.counterparty_id == entry.counterparty_id,
                Entry.invoice_number == entry.invoice_number,
                Entry.id != entry.id,
            )
        ).first()
        if duplicate is not None:
            found.append(
                EntryWarning(
                    "duplicate_invoice_number",
                    f"Another entry from this counterparty has invoice number "
                    f"{entry.invoice_number}.",
                )
            )
    if entry.category_id is None:
        found.append(EntryWarning("missing_category", "This entry has no category yet."))
    if entry.counterparty_id is None:
        found.append(EntryWarning("missing_counterparty", "This entry has no counterparty yet."))
    return found


# --- Writing -------------------------------------------------------------------------------


@dataclass(frozen=True)
class PaymentInstruction:
    """What to do with an entry's payments when it is saved.

    - paid:   replace every payment with one payment for the full gross (on `paid_on`)
    - unpaid: delete every payment
    - keep:   leave the payments alone (update only)
    """

    mode: str  # paid, unpaid or keep
    paid_on: date | None = None

    @classmethod
    def paid(cls, paid_on: date) -> "PaymentInstruction":
        return cls("paid", paid_on)

    @classmethod
    def unpaid(cls) -> "PaymentInstruction":
        return cls("unpaid")

    @classmethod
    def keep(cls) -> "PaymentInstruction":
        return cls("keep")


def _check_instruction(instruction: PaymentInstruction, *, allow_keep: bool) -> None:
    if instruction.mode not in {"paid", "unpaid", "keep"} or (
        instruction.mode == "keep" and not allow_keep
    ):
        allowed = "paid, unpaid or keep" if allow_keep else "paid or unpaid"
        raise ValidationFailed(
            f"The payment mode must be {allowed}.", fields={"payment.mode": f"Use {allowed}."}
        )
    if instruction.mode == "paid" and instruction.paid_on is None:
        raise ValidationFailed(
            "Enter the payment date.", fields={"payment.paid_on": "Enter the payment date."}
        )


def _apply_payment_instruction(
    session: Session, entry_id: int, gross_cents: int, instruction: PaymentInstruction
) -> None:
    if instruction.mode == "keep":
        return
    session.exec(delete(Payment).where(col(Payment.entry_id) == entry_id))
    if instruction.mode == "paid" and gross_cents > 0:
        assert instruction.paid_on is not None
        session.add(
            Payment(
                entry_id=entry_id,
                paid_on=instruction.paid_on,
                amount_cents=gross_cents,
                source=PaymentSource.MANUAL,
            )
        )


def create_entry(
    session: Session,
    company: Company,
    data: EntryInput,
    paid_on: date | None = None,
    payment: PaymentInstruction | None = None,
) -> Entry:
    """A manual, confirmed entry.

    `payment` decides its payments (paid or unpaid). Without it, the older `paid_on`
    shortcut applies: a date records one payment for the full amount, no date means unpaid.
    """
    assert company.id is not None
    if payment is None:
        payment = PaymentInstruction.paid(paid_on) if paid_on else PaymentInstruction.unpaid()
    _check_instruction(payment, allow_keep=False)
    prepared = _prepare(session, company, data)
    now = utc_now()
    entry = Entry(
        company_id=company.id,
        source=EntrySource.MANUAL,
        status=EntryStatus.CONFIRMED,
        confirmed_at=now,
        invoice_date=data.invoice_date,
        direction=data.direction,
        created_at=now,
        updated_at=now,
    )
    _apply_header(entry, prepared)
    session.add(entry)
    session.flush()
    assert entry.id is not None
    _write_lines(session, entry.id, prepared)
    _apply_payment_instruction(session, entry.id, prepared.gross, payment)
    session.commit()
    session.refresh(entry)
    return entry


def update_entry(
    session: Session,
    company: Company,
    entry_id: int,
    data: EntryInput,
    payment: PaymentInstruction | None = None,
) -> Entry:
    """Replace the header and the lines, and apply `payment` (default: keep), in one go.

    The source and status don't change.
    """
    assert company.id is not None
    payment = payment or PaymentInstruction.keep()
    _check_instruction(payment, allow_keep=True)
    entry = get_entry(session, company.id, entry_id)
    prepared = _prepare(session, company, data)
    paid = paid_cents_of(session, entry_id)
    if payment.mode == "keep" and prepared.gross < paid:
        raise Conflict(
            f"The new total ({format_cents(prepared.gross)}) is less than what has already "
            f"been paid ({format_cents(paid)}). Remove a payment first.",
            extra={"paid_cents": paid, "gross_cents": prepared.gross},
        )
    _apply_header(entry, prepared)
    entry.updated_at = utc_now()
    session.add(entry)
    session.exec(delete(EntryLine).where(col(EntryLine.entry_id) == entry_id))
    _write_lines(session, entry_id, prepared)
    _apply_payment_instruction(session, entry_id, prepared.gross, payment)
    session.commit()
    session.refresh(entry)
    return entry


def mark_paid(session: Session, company_id: int, entry_id: int, paid_on: date) -> Payment:
    """Record one payment for whatever remains to be paid; 409 when nothing remains."""
    entry = get_entry(session, company_id, entry_id)
    remaining = entry.total_gross_cents - paid_cents_of(session, entry_id)
    if remaining <= 0:
        raise Conflict("This entry is already fully paid.")
    payment = Payment(
        entry_id=entry_id, paid_on=paid_on, amount_cents=remaining, source=PaymentSource.MANUAL
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


@dataclass(frozen=True)
class Suggestion:
    category_id: int | None = None
    vat_rate_bp: int | None = None
    matched_on: str | None = None  # counterparty, description or None


def suggest(
    session: Session,
    company_id: int,
    *,
    direction: Direction,
    counterparty_id: int | None = None,
    description: str | None = None,
) -> Suggestion:
    """Category and VAT rate of the most recent confirmed entry that looks alike.

    Same counterparty and direction first, then same description (case-insensitive,
    trimmed) and direction. The rate is the one of that entry's first line.
    """
    base = (
        select(Entry)
        .where(
            Entry.company_id == company_id,
            Entry.direction == direction,
            Entry.status == EntryStatus.CONFIRMED,
        )
        .order_by(col(Entry.invoice_date).desc(), col(Entry.id).desc())
    )
    candidates: list[tuple[str, object]] = []
    if counterparty_id is not None:
        candidates.append(("counterparty", Entry.counterparty_id == counterparty_id))
    text = (description or "").strip().lower()
    if text:
        candidates.append(("description", func.lower(func.trim(Entry.description)) == text))
    for matched_on, condition in candidates:
        entry = session.exec(base.where(condition)).first()
        if entry is None:
            continue
        assert entry.id is not None
        rate = session.exec(
            select(EntryLine.vat_rate_bp)
            .where(EntryLine.entry_id == entry.id)
            .order_by(col(EntryLine.position), col(EntryLine.id))
        ).first()
        return Suggestion(entry.category_id, rate, matched_on)
    return Suggestion()


def confirm_entry(session: Session, company_id: int, entry_id: int) -> Entry:
    entry = get_entry(session, company_id, entry_id)
    if entry.status == EntryStatus.CONFIRMED:
        raise Conflict("This entry is already confirmed.")
    now = utc_now()
    entry.status = EntryStatus.CONFIRMED
    entry.confirmed_at = now
    entry.updated_at = now
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry(session: Session, company_id: int, entry_id: int) -> None:
    """Lines and payments go with it (ON DELETE CASCADE); the trigger skips its occurrence."""
    entry = get_entry(session, company_id, entry_id)
    session.delete(entry)
    session.commit()


def add_payment(
    session: Session,
    company_id: int,
    entry_id: int,
    *,
    paid_on: date,
    amount_cents: int,
    note: str | None = None,
) -> Payment:
    entry = get_entry(session, company_id, entry_id)
    if amount_cents <= 0:
        raise ValidationFailed(
            "Enter an amount above zero.", fields={"amount_cents": "Enter an amount above zero."}
        )
    remaining = entry.total_gross_cents - paid_cents_of(session, entry_id)
    if amount_cents > remaining:
        message = (
            f"This is more than the remaining amount ({format_cents(max(0, remaining))})."
            if remaining > 0
            else "This entry is already fully paid."
        )
        raise ValidationFailed(message, fields={"amount_cents": message})
    payment = Payment(
        entry_id=entry_id,
        paid_on=paid_on,
        amount_cents=amount_cents,
        source=PaymentSource.MANUAL,
        note=_clean(note),
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


def delete_payment(session: Session, company_id: int, payment_id: int) -> int:
    """Delete a payment of one of the company's entries; returns its entry id."""
    row = session.exec(
        select(Payment, Entry.company_id)
        .join(Entry, col(Entry.id) == Payment.entry_id)
        .where(Payment.id == payment_id)
    ).first()
    if row is None or row[1] != company_id:
        raise NotFound("This payment doesn't exist.")
    payment = row[0]
    session.delete(payment)
    session.commit()
    return payment.entry_id


# --- Listing -------------------------------------------------------------------------------

SORTS = {
    "invoice_date": col(Entry.invoice_date),
    "due_date": col(Entry.due_date),
    "amount": col(Entry.total_gross_cents),
}


@dataclass
class EntryFilters:
    direction: Direction | None = None
    status: EntryStatus | None = None
    payment_status: PaymentStatus | None = None
    category_id: int | None = None
    counterparty_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None
    sort: str = "-invoice_date"
    limit: int = 50
    offset: int = 0


@dataclass
class EntryListItem:
    entry: Entry
    paid_cents: int
    payment_status: PaymentStatus
    counterparty_name: str | None
    category_name: str | None


@dataclass
class EntrySummary:
    income_gross_cents: int = 0
    expense_gross_cents: int = 0
    income_net_cents: int = 0
    expense_net_cents: int = 0


@dataclass
class EntryPage:
    items: list[EntryListItem] = field(default_factory=list)
    total: int = 0
    summary: EntrySummary = field(default_factory=EntrySummary)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_entries(
    session: Session, company_id: int, filters: EntryFilters, today: date
) -> EntryPage:
    counterparty = aliased(Counterparty)
    category = aliased(Category)
    paid = paid_cents_expr()
    status = payment_status_expr(today, paid)

    conditions = [Entry.company_id == company_id]
    if filters.direction is not None:
        conditions.append(Entry.direction == filters.direction)
    if filters.status is not None:
        conditions.append(Entry.status == filters.status)
    if filters.payment_status is not None:
        conditions.append(status == filters.payment_status.value)
    if filters.category_id is not None:
        conditions.append(Entry.category_id == filters.category_id)
    if filters.counterparty_id is not None:
        conditions.append(Entry.counterparty_id == filters.counterparty_id)
    if filters.date_from is not None:
        conditions.append(col(Entry.invoice_date) >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(col(Entry.invoice_date) <= filters.date_to)
    if filters.q and filters.q.strip():
        pattern = f"%{_escape_like(filters.q.strip())}%"
        conditions.append(
            or_(
                col(Entry.description).like(pattern, escape="\\"),
                col(Entry.invoice_number).like(pattern, escape="\\"),
                col(counterparty.name).like(pattern, escape="\\"),
            )
        )

    def base(*columns):
        return (
            select(*columns)
            .select_from(Entry)
            .outerjoin(counterparty, col(counterparty.id) == Entry.counterparty_id)
            .outerjoin(category, col(category.id) == Entry.category_id)
            .where(*conditions)
        )

    income = Entry.direction == Direction.INCOME.value
    expense = Entry.direction == Direction.EXPENSE.value
    total, income_gross, expense_gross, income_net, expense_net = session.exec(
        base(
            func.count(),
            func.coalesce(func.sum(case((income, Entry.total_gross_cents), else_=0)), 0),
            func.coalesce(func.sum(case((expense, Entry.total_gross_cents), else_=0)), 0),
            func.coalesce(func.sum(case((income, Entry.total_net_cents), else_=0)), 0),
            func.coalesce(func.sum(case((expense, Entry.total_net_cents), else_=0)), 0),
        )
    ).one()

    descending = filters.sort.startswith("-")
    sort_column = SORTS.get(filters.sort.lstrip("-"), SORTS["invoice_date"])
    order = [
        sort_column.is_(None),  # undated (no due date) last, either way
        sort_column.desc() if descending else sort_column.asc(),
        col(Entry.id).desc() if descending else col(Entry.id).asc(),
    ]
    rows = session.exec(
        base(Entry, paid, status, counterparty.name, category.name)
        .order_by(*order)
        .limit(filters.limit)
        .offset(filters.offset)
    ).all()
    return EntryPage(
        items=[
            EntryListItem(e, p, PaymentStatus(s), cp_name, cat_name)
            for e, p, s, cp_name, cat_name in rows
        ],
        total=total,
        summary=EntrySummary(income_gross, expense_gross, income_net, expense_net),
    )
