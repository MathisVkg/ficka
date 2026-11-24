"""Demo data for development: fictional counterparties and N months of entries.

Everything goes through the normal services, so the data obeys every rule. The random
generator is seeded, so the same command gives the same data. All names are fictional.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlmodel import Session, select

from app.models import Category, Company, Counterparty, CounterpartyRole, Direction
from app.services import vat
from app.services.ledger import entries
from app.services.reference import counterparties as counterparty_service


@dataclass
class DemoResult:
    counterparties: int = 0
    income: int = 0
    expenses: int = 0
    payments: int = 0
    unpaid: int = 0
    partial: int = 0
    by_category: dict[str, int] = field(default_factory=dict)


def _vat_number(rng: random.Random) -> str:
    first8 = rng.randint(2_000_000, 19_999_999)  # 8 digits starting with 0 or 1
    return f"BE{first8:08d}{97 - first8 % 97:02d}"


def _iban(rng: random.Random) -> str:
    first10 = rng.randint(1_000_000_000, 9_999_999_999)
    check = first10 % 97 or 97
    bban = f"{first10:010d}{check:02d}"
    iban_check = 98 - int(bban + "111400") % 97  # B=11, E=14, then "00"
    return f"BE{iban_check:02d}{bban}"


# (name, role, default category, default VAT rate)
COUNTERPARTIES: list[tuple[str, CounterpartyRole, str | None, int | None]] = [
    ("Atelier Lune SRL", CounterpartyRole.CUSTOMER, "Services", 2100),
    ("Studio Nimbus BV", CounterpartyRole.CUSTOMER, "Services", 2100),
    ("Boulangerie Fictive SA", CounterpartyRole.CUSTOMER, "Goods", 600),
    ("Maison Exemple ASBL", CounterpartyRole.CUSTOMER, "Services", 2100),
    ("Imprimerie Imaginaire SC", CounterpartyRole.BOTH, "Office supplies", 2100),
    ("Propriétés Démo SA", CounterpartyRole.SUPPLIER, "Rent & premises", None),
    ("Énergie Fantaisie", CounterpartyRole.SUPPLIER, "Energy & utilities", 2100),
    ("Télécom Fictif", CounterpartyRole.SUPPLIER, "Telecom & internet", 2100),
    ("Logiciel Nuage", CounterpartyRole.SUPPLIER, "Software & subscriptions", 2100),
    ("Assurances Pastiche", CounterpartyRole.SUPPLIER, "Insurance", None),
    ("Cabinet Comptable Exemple", CounterpartyRole.SUPPLIER, "Professional fees", 2100),
    ("Brasserie du Coin Fictif", CounterpartyRole.SUPPLIER, "Restaurants & reception", 1200),
]


def _add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    return date(year, month % 12 + 1, 1)


def generate(session: Session, company: Company, months: int, today: date) -> DemoResult:
    assert company.id is not None
    rng = random.Random(2026)
    result = DemoResult()
    known_rates = vat.known_rate_set(session, company.country_code)

    categories = {
        (c.direction, c.name): c.id
        for c in session.exec(select(Category).where(Category.company_id == company.id))
    }

    def category_id(direction: Direction, name: str | None) -> int | None:
        return categories.get((direction, name)) if name else None

    parties: dict[str, int] = {}
    for name, role, default_category, default_rate in COUNTERPARTIES:
        existing = session.exec(
            select(Counterparty).where(
                Counterparty.company_id == company.id, Counterparty.name == name
            )
        ).first()
        if existing is not None:
            assert existing.id is not None
            parties[name] = existing.id
            continue
        direction = Direction.INCOME if role == CounterpartyRole.CUSTOMER else Direction.EXPENSE
        created = counterparty_service.create_counterparty(
            session,
            company.id,
            counterparty_service.CounterpartyInput(
                name=name,
                role=role,
                vat_number=_vat_number(rng),
                ibans=[_iban(rng)],
                default_category_id=category_id(direction, default_category),
                default_vat_rate_bp=default_rate if default_rate in known_rates else None,
            ),
            known_rates,
        )
        assert created.id is not None
        parties[name] = created.id
        result.counterparties += 1

    def add(
        direction: Direction,
        invoice_date: date,
        party: str,
        category: str,
        lines: list[tuple[str, int, int | None]],
        *,
        include_vat: bool = False,
        due_days: int = 30,
        number: str | None = None,
        pay: str = "auto",
    ) -> None:
        if invoice_date > today:
            return
        data = entries.EntryInput(
            direction=direction,
            invoice_date=invoice_date,
            due_date=invoice_date + timedelta(days=due_days),
            counterparty_id=parties[party],
            category_id=category_id(direction, category),
            description=lines[0][0],
            invoice_number=number,
            amounts_include_vat=include_vat,
            lines=[
                entries.LineInput(
                    description=desc,
                    gross_cents=amount if include_vat else None,
                    net_cents=None if include_vat else amount,
                    vat_rate_bp=rate,
                )
                for desc, amount, rate in lines
            ],
        )
        entry = entries.create_entry(session, company, data)
        assert entry.id is not None
        if direction == Direction.INCOME:
            result.income += 1
        else:
            result.expenses += 1
        result.by_category[category] = result.by_category.get(category, 0) + 1

        age = (today - invoice_date).days
        if pay == "auto":
            pay = "full" if age > 45 or rng.random() < 0.5 else "none"
        if pay == "full":
            paid_on = min(today, invoice_date + timedelta(days=rng.randint(0, due_days)))
            entries.add_payment(
                session,
                company.id,
                entry.id,
                paid_on=paid_on,
                amount_cents=entry.total_gross_cents,
            )
            result.payments += 1
        elif pay == "partial":
            entries.add_payment(
                session,
                company.id,
                entry.id,
                paid_on=min(today, invoice_date + timedelta(days=7)),
                amount_cents=entry.total_gross_cents // 2,
                note="First instalment",
            )
            result.payments += 1
            result.partial += 1
        else:
            result.unpaid += 1

    invoice_number = 0
    income, expense = Direction.INCOME, Direction.EXPENSE
    first_month = _add_months(date(today.year, today.month, 1), -(months - 1))
    for index in range(months):
        month = _add_months(first_month, index)
        recent = index == months - 1

        # Recurring costs
        add(
            expense,
            month,
            "Propriétés Démo SA",
            "Rent & premises",
            [("Office rent", 125_000, None)],
            due_days=5,
        )
        add(
            expense,
            month + timedelta(days=3),
            "Logiciel Nuage",
            "Software & subscriptions",
            [("Accounting software", 2_900, 2100), ("Cloud storage", 999, 2100)],
            due_days=0,
            pay="full",
        )
        add(
            expense,
            month + timedelta(days=9),
            "Télécom Fictif",
            "Telecom & internet",
            [("Internet and mobile", 7_499, 2100)],
            include_vat=True,
            due_days=20,
        )
        add(
            expense,
            month + timedelta(days=14),
            "Énergie Fantaisie",
            "Energy & utilities",
            [("Electricity", rng.randint(9_000, 21_000), 2100)],
            due_days=15,
            pay="none" if recent else "auto",
        )
        if month.month % 3 == 1:
            add(
                expense,
                month + timedelta(days=4),
                "Assurances Pastiche",
                "Insurance",
                [("Professional liability insurance", 38_500, None)],
                due_days=30,
            )
        if month.month % 2 == 0:
            add(
                expense,
                month + timedelta(days=20),
                "Cabinet Comptable Exemple",
                "Professional fees",
                [("Bookkeeping", 45_000, 2100)],
                due_days=30,
            )
        if rng.random() < 0.6:
            add(
                expense,
                month + timedelta(days=rng.randint(5, 25)),
                "Brasserie du Coin Fictif",
                "Restaurants & reception",
                [("Client lunch", rng.randint(6_000, 18_000), 1200)],
                include_vat=True,
                due_days=0,
                pay="full",
            )

        # Customer invoices
        for _ in range(rng.randint(2, 4)):
            invoice_number += 1
            customer = rng.choice(["Atelier Lune SRL", "Studio Nimbus BV", "Maison Exemple ASBL"])
            days = rng.randint(1, 26)
            hours = rng.randint(8, 40)
            lines = [(f"Consulting, {hours} h", hours * 8_500, 2100)]
            if rng.random() < 0.3:
                lines.append(("Travel costs", rng.randint(2_000, 9_000), 2100))
            pay = "auto"
            if invoice_number % 9 == 0:
                pay = "none"  # becomes overdue once the due date passes
            elif invoice_number % 7 == 0:
                pay = "partial"
            add(
                income,
                month + timedelta(days=days),
                customer,
                "Services",
                lines,
                number=f"2026-{invoice_number:04d}",
                pay=pay,
            )
        if rng.random() < 0.5:
            invoice_number += 1
            add(
                income,
                month + timedelta(days=rng.randint(1, 26)),
                "Boulangerie Fictive SA",
                "Goods",
                [("Packaging boxes", rng.randint(20_000, 60_000), 600), ("Delivery", 2_500, 2100)],
                number=f"2026-{invoice_number:04d}",
            )
        if rng.random() < 0.4:
            invoice_number += 1
            add(
                income,
                month + timedelta(days=rng.randint(1, 26)),
                "Imprimerie Imaginaire SC",
                "Services",
                [("Layout design", rng.randint(30_000, 90_000), 2100)],
                number=f"2026-{invoice_number:04d}",
            )

    return result
