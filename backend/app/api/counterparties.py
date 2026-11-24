"""Counterparties: customers and suppliers."""

from fastapi import Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentCompany, DbSession, protected_router
from app.models import Counterparty, CounterpartyRole
from app.services import vat
from app.services.reference import counterparties as service

router = protected_router(prefix="/counterparties", tags=["counterparties"])


class CounterpartyIn(BaseModel):
    name: str = Field(max_length=200)
    role: CounterpartyRole = CounterpartyRole.SUPPLIER
    vat_number: str | None = Field(default=None, max_length=40)
    ibans: list[str] = Field(default_factory=list, max_length=20)
    default_category_id: int | None = None
    default_vat_rate_bp: int | None = Field(default=None, ge=0, le=10000)
    notes: str | None = Field(default=None, max_length=2000)

    def to_input(self) -> service.CounterpartyInput:
        return service.CounterpartyInput(**self.model_dump())


class CounterpartyListItem(BaseModel):
    id: int
    name: str
    role: CounterpartyRole
    vat_number: str | None
    default_category_id: int | None
    default_vat_rate_bp: int | None
    entries_count: int
    open_balance_cents: int


class CounterpartyList(BaseModel):
    items: list[CounterpartyListItem]
    total: int


class StatsOut(BaseModel):
    entries_count: int
    income_total_cents: int
    expense_total_cents: int
    open_balance_cents: int


class CounterpartyOut(BaseModel):
    id: int
    name: str
    role: CounterpartyRole
    vat_number: str | None
    ibans: list[str]
    default_category_id: int | None
    default_vat_rate_bp: int | None
    notes: str | None
    stats: StatsOut


class CounterpartyDeleted(BaseModel):
    detached_entries: int


def detail(session, counterparty: Counterparty) -> CounterpartyOut:
    assert counterparty.id is not None
    stats = service.stats_of(session, counterparty.id)
    return CounterpartyOut(
        id=counterparty.id,
        name=counterparty.name,
        role=counterparty.role,
        vat_number=counterparty.vat_number,
        ibans=service.ibans_of(session, counterparty.id),
        default_category_id=counterparty.default_category_id,
        default_vat_rate_bp=counterparty.default_vat_rate_bp,
        notes=counterparty.notes,
        stats=StatsOut(**stats.__dict__),
    )


@router.get("", response_model=CounterpartyList)
def list_counterparties(
    session: DbSession,
    company: CurrentCompany,
    q: str | None = Query(default=None, max_length=200),
    role: CounterpartyRole | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CounterpartyList:
    assert company.id is not None
    rows, total = service.list_counterparties(
        session, company.id, q=q, role=role, limit=limit, offset=offset
    )
    items = []
    for counterparty, entries_count, open_balance in rows:
        assert counterparty.id is not None
        items.append(
            CounterpartyListItem(
                id=counterparty.id,
                name=counterparty.name,
                role=counterparty.role,
                vat_number=counterparty.vat_number,
                default_category_id=counterparty.default_category_id,
                default_vat_rate_bp=counterparty.default_vat_rate_bp,
                entries_count=entries_count,
                open_balance_cents=open_balance,
            )
        )
    return CounterpartyList(items=items, total=total)


@router.get("/{counterparty_id}", response_model=CounterpartyOut)
def get_counterparty(counterparty_id: int, session: DbSession, company: CurrentCompany):
    assert company.id is not None
    return detail(session, service.get_counterparty(session, company.id, counterparty_id))


@router.post("", response_model=CounterpartyOut, status_code=status.HTTP_201_CREATED)
def create_counterparty(body: CounterpartyIn, session: DbSession, company: CurrentCompany):
    assert company.id is not None
    counterparty = service.create_counterparty(
        session, company.id, body.to_input(), vat.known_rate_set(session, company.country_code)
    )
    return detail(session, counterparty)


@router.patch("/{counterparty_id}", response_model=CounterpartyOut)
def update_counterparty(
    counterparty_id: int, body: CounterpartyIn, session: DbSession, company: CurrentCompany
):
    """Updates every field; `ibans` replaces the existing list."""
    assert company.id is not None
    counterparty = service.update_counterparty(
        session,
        company.id,
        counterparty_id,
        body.to_input(),
        vat.known_rate_set(session, company.country_code),
    )
    return detail(session, counterparty)


@router.delete("/{counterparty_id}", response_model=CounterpartyDeleted)
def delete_counterparty(counterparty_id: int, session: DbSession, company: CurrentCompany):
    assert company.id is not None
    detached = service.delete_counterparty(session, company.id, counterparty_id)
    return CounterpartyDeleted(detached_entries=detached)
