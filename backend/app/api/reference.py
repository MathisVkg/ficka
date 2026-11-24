"""VAT rates, company settings and categories."""

from datetime import date

from fastapi import Query, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentCompany, DbSession, protected_router
from app.models import Category, CompanySettings, Direction
from app.services import vat
from app.services.clock import Today
from app.services.reference import categories as category_service

router = protected_router(tags=["reference"])


# --- VAT rates -----------------------------------------------------------------------------


class VatRateOut(BaseModel):
    rate_bp: int
    label: str


@router.get("/vat-rates", response_model=list[VatRateOut])
def list_vat_rates(
    session: DbSession, company: CurrentCompany, today: Today, on: date | None = None
) -> list[VatRateOut]:
    rates = vat.rates_valid_on(session, company.country_code, on or today)
    return [VatRateOut(rate_bp=r.rate_bp, label=r.label) for r in rates]


# --- Company settings (read-only for now) ---------------------------------------------------


class CompanySettingsOut(BaseModel):
    amounts_include_vat_default: bool
    locale: str
    country_code: str
    currency: str


@router.get("/company/settings", response_model=CompanySettingsOut)
def company_settings(session: DbSession, company: CurrentCompany) -> CompanySettingsOut:
    settings = session.get(CompanySettings, company.id)
    return CompanySettingsOut(
        amounts_include_vat_default=settings.amounts_include_vat_default if settings else False,
        locale=settings.locale if settings else "en",
        country_code=company.country_code,
        currency=company.currency,
    )


# --- Categories ----------------------------------------------------------------------------


class UsageOut(BaseModel):
    entries: int
    templates: int
    counterparties: int


class CategoryOut(BaseModel):
    id: int
    direction: Direction
    name: str
    default_vat_rate_bp: int | None
    position: int
    is_seeded: bool
    usage: UsageOut


class CategoryCreate(BaseModel):
    direction: Direction
    name: str = Field(min_length=1, max_length=120)
    default_vat_rate_bp: int | None = Field(default=None, ge=0, le=10000)


class CategoryUpdate(BaseModel):
    direction: Direction | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    default_vat_rate_bp: int | None = Field(default=None, ge=0, le=10000)
    position: int | None = Field(default=None, ge=0)


class CategoryReorder(BaseModel):
    direction: Direction
    ids: list[int]


class CategoryDeleted(BaseModel):
    moved: UsageOut


def category_out(category: Category, usage: category_service.CategoryUsage) -> CategoryOut:
    assert category.id is not None
    return CategoryOut(
        id=category.id,
        direction=category.direction,
        name=category.name,
        default_vat_rate_bp=category.default_vat_rate_bp,
        position=category.position,
        is_seeded=category.is_seeded,
        usage=UsageOut(
            entries=usage.entries, templates=usage.templates, counterparties=usage.counterparties
        ),
    )


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    session: DbSession, company: CurrentCompany, direction: Direction | None = None
) -> list[CategoryOut]:
    assert company.id is not None
    return [
        category_out(c, u)
        for c, u in category_service.list_categories(session, company.id, direction)
    ]


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryCreate, session: DbSession, company: CurrentCompany):
    assert company.id is not None
    category = category_service.create_category(
        session,
        company.id,
        direction=body.direction,
        name=body.name,
        default_vat_rate_bp=body.default_vat_rate_bp,
        known_rates=vat.known_rate_set(session, company.country_code),
    )
    assert category.id is not None
    return category_out(category, category_service.usage_of(session, category.id))


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, body: CategoryUpdate, session: DbSession, company: CurrentCompany
):
    assert company.id is not None
    changes = body.model_dump(exclude_unset=True)
    for key in ("direction", "name", "position"):
        if key in changes and changes[key] is None:
            changes.pop(key)
    category = category_service.update_category(
        session,
        company.id,
        category_id,
        changes,
        known_rates=vat.known_rate_set(session, company.country_code),
    )
    return category_out(category, category_service.usage_of(session, category_id))


@router.post("/categories/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_categories(body: CategoryReorder, session: DbSession, company: CurrentCompany):
    assert company.id is not None
    category_service.reorder_categories(session, company.id, body.direction, body.ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/categories/{category_id}", response_model=CategoryDeleted)
def delete_category(
    category_id: int,
    session: DbSession,
    company: CurrentCompany,
    reassign_to: int | None = Query(default=None),
) -> CategoryDeleted:
    assert company.id is not None
    usage = category_service.delete_category(session, company.id, category_id, reassign_to)
    return CategoryDeleted(
        moved=UsageOut(
            entries=usage.entries, templates=usage.templates, counterparties=usage.counterparties
        )
    )
