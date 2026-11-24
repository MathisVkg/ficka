"""Counterparties (customers and suppliers), with their IBANs. Always scoped by company."""

from dataclasses import dataclass, field

from sqlalchemy import case, delete, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.errors import Conflict, NotFound, ValidationFailed
from app.models import (
    Counterparty,
    CounterpartyIban,
    CounterpartyRole,
    Direction,
    Entry,
    EntryStatus,
)
from app.models.base import utc_now
from app.services import identifiers
from app.services.ledger.payment_status import paid_cents_expr
from app.services.reference.categories import get_category


@dataclass
class CounterpartyInput:
    name: str
    role: CounterpartyRole = CounterpartyRole.SUPPLIER
    vat_number: str | None = None
    ibans: list[str] = field(default_factory=list)
    default_category_id: int | None = None
    default_vat_rate_bp: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CounterpartyStats:
    entries_count: int
    income_total_cents: int
    expense_total_cents: int
    open_balance_cents: int


def get_counterparty(session: Session, company_id: int, counterparty_id: int) -> Counterparty:
    counterparty = session.get(Counterparty, counterparty_id)
    if counterparty is None or counterparty.company_id != company_id:
        raise NotFound("This counterparty doesn't exist.")
    return counterparty


def ibans_of(session: Session, counterparty_id: int) -> list[str]:
    return list(
        session.exec(
            select(CounterpartyIban.iban)
            .where(CounterpartyIban.counterparty_id == counterparty_id)
            .order_by(col(CounterpartyIban.id))
        ).all()
    )


def _remaining_signed():
    """Open amount of an entry: positive for income (owed to us), negative for expenses."""
    remaining = Entry.total_gross_cents - paid_cents_expr()
    return case((Entry.direction == Direction.INCOME.value, remaining), else_=-remaining)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_counterparties(
    session: Session,
    company_id: int,
    *,
    q: str | None = None,
    role: CounterpartyRole | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[tuple[Counterparty, int, int]], int]:
    """(counterparty, entries_count, open_balance_cents) rows, and the total count."""
    entries_count = (
        select(func.count())
        .select_from(Entry)
        .where(Entry.counterparty_id == Counterparty.id)
        .correlate(Counterparty)
        .scalar_subquery()
    )
    open_balance = (
        select(func.coalesce(func.sum(_remaining_signed()), 0))
        .where(Entry.counterparty_id == Counterparty.id, Entry.status == EntryStatus.CONFIRMED)
        .correlate(Counterparty)
        .scalar_subquery()
    )
    filters = [Counterparty.company_id == company_id]
    if q and q.strip():
        text = f"%{_escape_like(q.strip())}%"
        compact = f"%{_escape_like(identifiers._compact(q))}%"
        iban_match = (
            select(CounterpartyIban.id)
            .where(
                CounterpartyIban.counterparty_id == Counterparty.id,
                col(CounterpartyIban.iban).like(compact, escape="\\"),
            )
            .correlate(Counterparty)
            .exists()
        )
        filters.append(
            or_(
                col(Counterparty.name).like(text, escape="\\"),
                col(Counterparty.vat_number).like(compact, escape="\\"),
                iban_match,
            )
        )
    if role is not None:
        if role == CounterpartyRole.BOTH:
            filters.append(Counterparty.role == CounterpartyRole.BOTH)
        else:
            filters.append(col(Counterparty.role).in_([role.value, CounterpartyRole.BOTH.value]))

    total = session.exec(select(func.count()).select_from(Counterparty).where(*filters)).one()
    rows = session.exec(
        select(Counterparty, entries_count, open_balance)
        .where(*filters)
        .order_by(func.lower(Counterparty.name), col(Counterparty.id))
        .limit(limit)
        .offset(offset)
    ).all()
    return [(c, n, b) for c, n, b in rows], total


def stats_of(session: Session, counterparty_id: int) -> CounterpartyStats:
    """Totals over the counterparty's confirmed entries."""
    gross = Entry.total_gross_cents
    row = session.exec(
        select(
            func.count(),
            func.coalesce(
                func.sum(case((Entry.direction == Direction.INCOME.value, gross), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((Entry.direction == Direction.EXPENSE.value, gross), else_=0)), 0
            ),
            func.coalesce(func.sum(_remaining_signed()), 0),
        ).where(Entry.counterparty_id == counterparty_id, Entry.status == EntryStatus.CONFIRMED)
    ).one()
    return CounterpartyStats(*row)


def _normalize(
    session: Session, company_id: int, data: CounterpartyInput, known_rates: set[int]
) -> tuple[str, str | None, list[str], str | None]:
    errors: dict[str, str] = {}
    name = data.name.strip()
    if not name:
        errors["name"] = "Enter a name."
    vat_number = None
    if data.vat_number and data.vat_number.strip():
        try:
            vat_number = identifiers.normalize_vat_number(data.vat_number)
        except identifiers.IdentifierError as exc:
            errors["vat_number"] = str(exc)
    ibans: list[str] = []
    for index, raw in enumerate(data.ibans):
        if not raw.strip():
            continue
        try:
            iban = identifiers.normalize_iban(raw)
        except identifiers.IdentifierError as exc:
            errors[f"ibans.{index}"] = str(exc)
            continue
        if iban not in ibans:
            ibans.append(iban)
    if data.default_category_id is not None:
        try:
            get_category(session, company_id, data.default_category_id)
        except NotFound:
            errors["default_category_id"] = "Choose one of your categories."
    if data.default_vat_rate_bp is not None and data.default_vat_rate_bp not in known_rates:
        errors["default_vat_rate_bp"] = "Choose one of the VAT rates, or no VAT."
    notes = data.notes.strip() if data.notes and data.notes.strip() else None
    if errors:
        raise ValidationFailed("Some fields are invalid.", fields=errors)
    return name, vat_number, ibans, notes


def _check_vat_free(
    session: Session, company_id: int, vat_number: str | None, exclude_id: int | None
) -> None:
    if vat_number is None:
        return
    query = select(Counterparty.id, Counterparty.name).where(
        Counterparty.company_id == company_id, Counterparty.vat_number == vat_number
    )
    if exclude_id is not None:
        query = query.where(Counterparty.id != exclude_id)
    existing = session.exec(query).first()
    if existing is not None:
        message = f"“{existing[1]}” already has this VAT number."
        raise Conflict(message, fields={"vat_number": message}, extra={"existing_id": existing[0]})


def _apply(
    session: Session,
    counterparty: Counterparty,
    data: CounterpartyInput,
    name: str,
    vat_number: str | None,
    ibans: list[str],
    notes: str | None,
) -> None:
    counterparty.name = name
    counterparty.role = data.role
    counterparty.vat_number = vat_number
    counterparty.default_category_id = data.default_category_id
    counterparty.default_vat_rate_bp = data.default_vat_rate_bp
    counterparty.notes = notes
    counterparty.updated_at = utc_now()
    session.add(counterparty)
    session.flush()
    assert counterparty.id is not None
    session.exec(
        delete(CounterpartyIban).where(col(CounterpartyIban.counterparty_id) == counterparty.id)
    )
    for iban in ibans:
        session.add(CounterpartyIban(counterparty_id=counterparty.id, iban=iban))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise Conflict(
            "Another counterparty already has this VAT number.",
            fields={"vat_number": "Another counterparty already has this VAT number."},
        ) from exc
    session.refresh(counterparty)


def create_counterparty(
    session: Session, company_id: int, data: CounterpartyInput, known_rates: set[int]
) -> Counterparty:
    name, vat_number, ibans, notes = _normalize(session, company_id, data, known_rates)
    _check_vat_free(session, company_id, vat_number, None)
    counterparty = Counterparty(company_id=company_id, name=name)
    _apply(session, counterparty, data, name, vat_number, ibans, notes)
    return counterparty


def update_counterparty(
    session: Session,
    company_id: int,
    counterparty_id: int,
    data: CounterpartyInput,
    known_rates: set[int],
) -> Counterparty:
    counterparty = get_counterparty(session, company_id, counterparty_id)
    name, vat_number, ibans, notes = _normalize(session, company_id, data, known_rates)
    _check_vat_free(session, company_id, vat_number, counterparty_id)
    _apply(session, counterparty, data, name, vat_number, ibans, notes)
    return counterparty


def delete_counterparty(session: Session, company_id: int, counterparty_id: int) -> int:
    """Delete it; its entries keep their data and lose the link. Returns how many."""
    counterparty = get_counterparty(session, company_id, counterparty_id)
    detached = session.exec(
        select(func.count()).select_from(Entry).where(Entry.counterparty_id == counterparty_id)
    ).one()
    session.delete(counterparty)
    session.commit()
    return detached
