"""Idempotent seed data: running it again changes nothing.

- VAT configuration: Belgium and its rates (as in docs/schema.sql).
- For each company: its `company_settings` row and the default categories
  (docs/database.md), marked `is_seeded = 1`.

Default categories are created once per company. If a company already has
seeded categories, they are left alone, so categories the user renamed or
deleted are not brought back.
"""

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, select

from app.models import Category, Company, CompanySettings, Direction, VatCountry, VatRate

VAT_COUNTRIES: list[tuple[str, str]] = [("BE", "Belgium")]

# (country, rate in basis points, label, valid from)
VAT_RATES: list[tuple[str, int, str, date]] = [
    ("BE", 2100, "Standard 21 %", date(2000, 1, 1)),
    ("BE", 1200, "Reduced 12 %", date(2000, 1, 1)),
    ("BE", 600, "Reduced 6 %", date(2000, 1, 1)),
    ("BE", 0, "Zero 0 %", date(2000, 1, 1)),
]

# (direction, name, default VAT rate in basis points or None for no VAT)
DEFAULT_CATEGORIES: list[tuple[Direction, str, int | None]] = [
    (Direction.INCOME, "Services", 2100),
    (Direction.INCOME, "Goods", 2100),
    (Direction.INCOME, "Other income", None),
    (Direction.EXPENSE, "Rent & premises", None),
    (Direction.EXPENSE, "Energy & utilities", 2100),
    (Direction.EXPENSE, "Telecom & internet", 2100),
    (Direction.EXPENSE, "Software & subscriptions", 2100),
    (Direction.EXPENSE, "Office supplies", 2100),
    (Direction.EXPENSE, "Equipment", 2100),
    (Direction.EXPENSE, "Vehicle & fuel", 2100),
    (Direction.EXPENSE, "Travel", 2100),
    (Direction.EXPENSE, "Restaurants & reception", 1200),
    (Direction.EXPENSE, "Insurance", None),
    (Direction.EXPENSE, "Professional fees", 2100),
    (Direction.EXPENSE, "Bank fees", None),
    (Direction.EXPENSE, "Salaries & social charges", None),
    (Direction.EXPENSE, "Taxes & contributions", None),
    (Direction.EXPENSE, "Marketing", 2100),
    (Direction.EXPENSE, "Training", 2100),
    (Direction.EXPENSE, "Other", 2100),
]


@dataclass
class SeedResult:
    countries: int = 0
    rates: int = 0
    settings: int = 0
    categories: int = 0

    @property
    def total(self) -> int:
        return self.countries + self.rates + self.settings + self.categories


def seed_vat(session: Session, result: SeedResult) -> None:
    for code, name in VAT_COUNTRIES:
        if session.get(VatCountry, code) is None:
            session.add(VatCountry(code=code, name=name))
            result.countries += 1
    session.flush()

    for country, rate_bp, label, valid_from in VAT_RATES:
        existing = session.exec(
            select(VatRate).where(
                VatRate.country_code == country,
                VatRate.rate_bp == rate_bp,
                VatRate.valid_from == valid_from,
            )
        ).first()
        if existing is None:
            session.add(
                VatRate(country_code=country, rate_bp=rate_bp, label=label, valid_from=valid_from)
            )
            result.rates += 1


def seed_company(session: Session, company_id: int, result: SeedResult) -> None:
    if session.get(CompanySettings, company_id) is None:
        session.add(CompanySettings(company_id=company_id))
        result.settings += 1

    already_seeded = session.exec(
        select(Category.id).where(Category.company_id == company_id, Category.is_seeded == True)  # noqa: E712
    ).first()
    if already_seeded is not None:
        return

    positions: dict[Direction, int] = {}
    for direction, name, vat_rate_bp in DEFAULT_CATEGORIES:
        position = positions.get(direction, 0)
        positions[direction] = position + 1
        existing = session.exec(
            select(Category.id).where(
                Category.company_id == company_id,
                Category.direction == direction,
                Category.name == name,
            )
        ).first()
        if existing is not None:  # a custom category with the same name already exists
            continue
        session.add(
            Category(
                company_id=company_id,
                direction=direction,
                name=name,
                default_vat_rate_bp=vat_rate_bp,
                is_seeded=True,
                position=position,
            )
        )
        result.categories += 1


def run_seed(session: Session) -> SeedResult:
    """Seed VAT data and every company, in one transaction."""
    result = SeedResult()
    seed_vat(session, result)
    for company_id in session.exec(select(Company.id)).all():
        assert company_id is not None
        seed_company(session, company_id, result)
    session.commit()
    return result
