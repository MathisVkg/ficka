from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Category, Entry
from app.schemas.financial import CategoryCreate, CategoryUpdate, EntryCreate, EntryUpdate


def vat_from_total(amount: Decimal, rate: Decimal) -> Decimal:
    return (amount * rate / (Decimal("100") + rate)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def normalize_name(name: str) -> tuple[str, str]:
    display = " ".join(name.split())
    if not display:
        raise HTTPException(422, "Category name is required")
    return display, display.casefold()


def commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            409, "This change conflicts with existing data or a category name"
        ) from None


def create_category(session: Session, data: CategoryCreate) -> Category:
    name, key = normalize_name(data.name)
    category = Category(name=name, name_key=key, type=data.type, color=data.color)
    session.add(category)
    commit(session)
    session.refresh(category)
    return category


def update_category(session: Session, category_id: UUID, data: CategoryUpdate) -> Category:
    category = session.scalar(select(Category).where(Category.id == category_id).with_for_update())
    if category is None:
        raise HTTPException(404, "Category not found")
    values = data.model_dump(exclude_unset=True)
    if "name" in values:
        values["name"], values["name_key"] = normalize_name(values["name"])
    for key, value in values.items():
        setattr(category, key, value)
    commit(session)
    session.refresh(category)
    return category


def get_entry(session: Session, kind: str, entry_id: UUID, lock=False) -> Entry:
    query = select(Entry).where(
        Entry.id == entry_id, Entry.type == kind, Entry.deleted_at.is_(None)
    )
    if lock:
        query = query.with_for_update()
    entry = session.scalar(query)
    if entry is None:
        raise HTTPException(404, "Entry not found")
    return entry


def validate_category(
    session: Session, kind: str, category_id: UUID | None, previous_id: UUID | None = None
) -> None:
    if category_id is None:
        return
    category = session.scalar(select(Category).where(Category.id == category_id).with_for_update())
    if category is None or category.type != kind:
        raise HTTPException(422, "Choose a category of the same entry type")
    if not category.active and category_id != previous_id:
        raise HTTPException(422, "Archived categories cannot be assigned to new entries")


def create_entry(session: Session, kind: str, data: EntryCreate) -> Entry:
    validate_category(session, kind, data.category_id)
    values = data.model_dump()
    overridden = values["vat_amount"] is not None
    if not overridden:
        values["vat_amount"] = vat_from_total(data.amount, data.vat_rate)
    entry = Entry(type=kind, **values, vat_overridden=overridden)
    session.add(entry)
    commit(session)
    session.refresh(entry)
    return entry


def update_entry(session: Session, kind: str, entry_id: UUID, data: EntryUpdate) -> Entry:
    entry = get_entry(session, kind, entry_id, lock=True)
    values = {key: getattr(entry, key) for key in EntryCreate.model_fields}
    if not entry.vat_overridden:
        values["vat_amount"] = None
    values.update(data.model_dump(exclude_unset=True))
    try:
        validated = EntryCreate.model_validate(values)
    except ValidationError as exc:
        raise HTTPException(
            422,
            {
                "message": "Check entry values",
                "fields": {".".join(map(str, e["loc"])) or "form": e["msg"] for e in exc.errors()},
            },
        ) from None
    validate_category(session, kind, validated.category_id, entry.category_id)
    values = validated.model_dump()
    entry.vat_overridden = values["vat_amount"] is not None
    if not entry.vat_overridden:
        values["vat_amount"] = vat_from_total(validated.amount, validated.vat_rate)
    for key, value in values.items():
        setattr(entry, key, value)
    # Even an unchanged status confirmation records an explicit write timestamp.
    entry.updated_at = datetime.now(UTC)
    commit(session)
    session.refresh(entry)
    return entry


def delete_entry(session: Session, kind: str, entry_id: UUID) -> None:
    entry = get_entry(session, kind, entry_id, lock=True)
    entry.deleted_at = datetime.now(UTC)
    commit(session)


def list_entries(
    session: Session,
    kind: str,
    *,
    page,
    page_size,
    date_from,
    date_to,
    status,
    category_id,
    search,
    sort,
    direction,
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "Start date must be on or before end date")
    conditions = [Entry.type == kind, Entry.deleted_at.is_(None)]
    if date_from:
        conditions.append(Entry.entry_date >= date_from)
    if date_to:
        conditions.append(Entry.entry_date <= date_to)
    if status:
        conditions.append(Entry.status == status)
    if category_id:
        conditions.append(Entry.category_id == category_id)
    if search:
        conditions.append(
            or_(
                Entry.title.icontains(search, autoescape=True),
                Entry.counterparty.icontains(search, autoescape=True),
                Entry.notes.icontains(search, autoescape=True),
            )
        )
    total = session.scalar(select(func.count()).select_from(Entry).where(*conditions))
    column = {"date": Entry.entry_date, "amount": Entry.amount, "created_at": Entry.created_at}[
        sort
    ]
    order = column.asc() if direction == "asc" else column.desc()
    items = session.scalars(
        select(Entry)
        .where(*conditions)
        .order_by(order, Entry.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}
