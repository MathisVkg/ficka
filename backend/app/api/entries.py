"""Entries and payments."""

from datetime import date, datetime

from fastapi import Query, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentCompany, DbSession, protected_router
from app.models import Direction, EntrySource, EntryStatus, PaymentSource
from app.services.clock import Today
from app.services.ledger import entries as service
from app.services.ledger.payment_status import PaymentStatus

router = protected_router(tags=["entries"])

TEXT = 500


# --- Request models ------------------------------------------------------------------------


class LineIn(BaseModel):
    description: str | None = Field(default=None, max_length=TEXT)
    net_cents: int | None = None
    gross_cents: int | None = None
    vat_rate_bp: int | None = None
    vat_cents: int | None = None
    vat_manual: bool = False


class EntryIn(BaseModel):
    direction: Direction
    invoice_date: date
    due_date: date | None = None
    counterparty_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=TEXT)
    invoice_number: str | None = Field(default=None, max_length=100)
    structured_reference: str | None = Field(default=None, max_length=40)
    amounts_include_vat: bool = False
    document_location: str | None = Field(default=None, max_length=2000)
    lines: list[LineIn]

    def to_input(self) -> service.EntryInput:
        data = self.model_dump(exclude={"lines", "paid_on"})
        return service.EntryInput(
            **data, lines=[service.LineInput(**line.model_dump()) for line in self.lines]
        )


class EntryCreate(EntryIn):
    paid_on: date | None = None


class PaymentIn(BaseModel):
    paid_on: date
    amount_cents: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=TEXT)


# --- Response models -----------------------------------------------------------------------


class Ref(BaseModel):
    id: int
    name: str


class LineOut(BaseModel):
    id: int
    position: int
    description: str | None
    net_cents: int
    vat_rate_bp: int | None
    vat_cents: int
    gross_cents: int
    vat_manual: bool


class PaymentOut(BaseModel):
    id: int
    paid_on: date
    amount_cents: int
    source: PaymentSource
    note: str | None


class WarningOut(BaseModel):
    code: str
    message: str


class EntrySummaryFields(BaseModel):
    id: int
    direction: Direction
    status: EntryStatus
    source: EntrySource
    invoice_date: date
    due_date: date | None
    counterparty: Ref | None
    category: Ref | None
    description: str | None
    invoice_number: str | None
    total_net_cents: int
    total_vat_cents: int
    total_gross_cents: int
    paid_cents: int
    payment_status: PaymentStatus


class EntryListItemOut(EntrySummaryFields):
    pass


class SummaryOut(BaseModel):
    income_gross_cents: int
    expense_gross_cents: int
    income_net_cents: int
    expense_net_cents: int


class EntryListOut(BaseModel):
    items: list[EntryListItemOut]
    total: int
    summary: SummaryOut


class EntryOut(EntrySummaryFields):
    structured_reference: str | None
    amounts_include_vat: bool
    document_location: str | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    remaining_cents: int
    lines: list[LineOut]
    payments: list[PaymentOut]
    warnings: list[WarningOut] = []


def _ref(ref_id: int | None, name: str | None) -> Ref | None:
    return Ref(id=ref_id, name=name) if ref_id is not None and name is not None else None


def _common(entry, paid, payment_status, counterparty_name, category_name) -> dict:
    return {
        "id": entry.id,
        "direction": entry.direction,
        "status": entry.status,
        "source": entry.source,
        "invoice_date": entry.invoice_date,
        "due_date": entry.due_date,
        "counterparty": _ref(entry.counterparty_id, counterparty_name),
        "category": _ref(entry.category_id, category_name),
        "description": entry.description,
        "invoice_number": entry.invoice_number,
        "total_net_cents": entry.total_net_cents,
        "total_vat_cents": entry.total_vat_cents,
        "total_gross_cents": entry.total_gross_cents,
        "paid_cents": paid,
        "payment_status": payment_status,
    }


def entry_out(session, company_id: int, entry_id: int, today: date, warnings=None) -> EntryOut:
    detail = service.entry_detail(session, company_id, entry_id, today)
    entry = detail.entry
    return EntryOut(
        **_common(
            entry,
            detail.paid_cents,
            detail.payment_status,
            detail.counterparty_name,
            detail.category_name,
        ),
        structured_reference=entry.structured_reference,
        amounts_include_vat=entry.amounts_include_vat,
        document_location=entry.document_location,
        confirmed_at=entry.confirmed_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        remaining_cents=detail.remaining_cents,
        lines=[
            LineOut(
                id=line.id,
                position=line.position,
                description=line.description,
                net_cents=line.net_cents,
                vat_rate_bp=line.vat_rate_bp,
                vat_cents=line.vat_cents,
                gross_cents=line.net_cents + line.vat_cents,
                vat_manual=line.vat_manual,
            )
            for line in detail.lines
        ],
        payments=[
            PaymentOut(
                id=p.id,
                paid_on=p.paid_on,
                amount_cents=p.amount_cents,
                source=p.source,
                note=p.note,
            )
            for p in detail.payments
        ],
        warnings=[WarningOut(code=w.code, message=w.message) for w in (warnings or [])],
    )


# --- Routes --------------------------------------------------------------------------------


@router.get("/entries", response_model=EntryListOut)
def list_entries(
    session: DbSession,
    company: CurrentCompany,
    today: Today,
    direction: Direction | None = None,
    status_: EntryStatus | None = Query(default=None, alias="status"),
    payment_status: PaymentStatus | None = None,
    category_id: int | None = None,
    counterparty_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, max_length=200),
    sort: str = Query(default="-invoice_date", pattern=r"^-?(invoice_date|due_date|amount)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EntryListOut:
    assert company.id is not None
    page = service.list_entries(
        session,
        company.id,
        service.EntryFilters(
            direction=direction,
            status=status_,
            payment_status=payment_status,
            category_id=category_id,
            counterparty_id=counterparty_id,
            date_from=date_from,
            date_to=date_to,
            q=q,
            sort=sort,
            limit=limit,
            offset=offset,
        ),
        today,
    )
    return EntryListOut(
        items=[
            EntryListItemOut(
                **_common(
                    item.entry,
                    item.paid_cents,
                    item.payment_status,
                    item.counterparty_name,
                    item.category_name,
                )
            )
            for item in page.items
        ],
        total=page.total,
        summary=SummaryOut(**page.summary.__dict__),
    )


@router.get("/entries/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: int, session: DbSession, company: CurrentCompany, today: Today):
    assert company.id is not None
    return entry_out(session, company.id, entry_id, today)


@router.post("/entries", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(body: EntryCreate, session: DbSession, company: CurrentCompany, today: Today):
    assert company.id is not None
    entry = service.create_entry(session, company, body.to_input(), paid_on=body.paid_on)
    assert entry.id is not None
    return entry_out(session, company.id, entry.id, today, service.warnings_for(session, entry))


@router.put("/entries/{entry_id}", response_model=EntryOut)
def update_entry(
    entry_id: int, body: EntryIn, session: DbSession, company: CurrentCompany, today: Today
):
    assert company.id is not None
    entry = service.update_entry(session, company, entry_id, body.to_input())
    return entry_out(session, company.id, entry_id, today, service.warnings_for(session, entry))


@router.post("/entries/{entry_id}/confirm", response_model=EntryOut)
def confirm_entry(entry_id: int, session: DbSession, company: CurrentCompany, today: Today):
    assert company.id is not None
    service.confirm_entry(session, company.id, entry_id)
    return entry_out(session, company.id, entry_id, today)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: int, session: DbSession, company: CurrentCompany):
    assert company.id is not None
    service.delete_entry(session, company.id, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/entries/{entry_id}/payments", response_model=EntryOut, status_code=status.HTTP_201_CREATED
)
def add_payment(
    entry_id: int, body: PaymentIn, session: DbSession, company: CurrentCompany, today: Today
):
    """Record a manual payment; returns the updated entry."""
    assert company.id is not None
    service.add_payment(
        session,
        company.id,
        entry_id,
        paid_on=body.paid_on,
        amount_cents=body.amount_cents,
        note=body.note,
    )
    return entry_out(session, company.id, entry_id, today)


@router.delete("/payments/{payment_id}", response_model=EntryOut)
def delete_payment(payment_id: int, session: DbSession, company: CurrentCompany, today: Today):
    """Delete a payment; returns the updated entry."""
    assert company.id is not None
    entry_id = service.delete_payment(session, company.id, payment_id)
    return entry_out(session, company.id, entry_id, today)
