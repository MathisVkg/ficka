from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.financial import EntryCreate
from app.services.financial import vat_from_total


@pytest.mark.parametrize(
    ("total", "rate", "expected"),
    [
        ("121.00", "21", "21.00"),
        ("106", "6", "6.00"),
        ("112", "12", "12.00"),
        ("0.03", "21", "0.01"),
        ("10.01", "0", "0.00"),
        ("102.50", "2.5", "2.50"),
        ("999999999999.99", "21", "173553719008.26"),
    ],
)
def test_exact_vat(total, rate, expected):
    assert vat_from_total(Decimal(total), Decimal(rate)) == Decimal(expected)


@pytest.mark.parametrize(
    "invalid",
    [
        {"amount": "-1"},
        {"amount": "0"},
        {"amount": "1.001"},
        {"amount": 1.1},
        {"amount": "NaN"},
        {"amount": "1000000000000"},
        {"vat_amount": "122"},
        {"vat_amount": "-0.01"},
        {"vat_rate": "101"},
        {"vat_rate": "0.00001"},
        {"entry_date": "2026-02-30"},
        {"entry_date": 0},
        {"entry_date": "2026-01-01T00:00:00"},
        {"currency": "ZZZ"},
        {"country": "XX"},
        {"title": "  "},
        {"status": "due"},
        {"unexpected_field": True},
    ],
)
def test_invalid_financial_input(invalid):
    with pytest.raises(ValidationError):
        EntryCreate.model_validate({"title": "Invoice", "amount": "121", **invalid})


def test_creation_date_default_and_manual_override():
    entry = EntryCreate(title="Invoice", amount="121", entry_date="2026-01-02")
    assert entry.payment_date == entry.entry_date
    manual = EntryCreate(title="Invoice", amount="121", vat_amount="20.10")
    assert manual.vat_amount == Decimal("20.10")
