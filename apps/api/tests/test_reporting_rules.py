from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.schemas.reporting import MovementTotals
from app.services.reporting import (
    add,
    difference,
    month_end,
    next_month,
    percentages,
    resolve_period,
)


def test_decimal_precision_and_serialization():
    assert add([Decimal("0.10"), Decimal("0.20")]) == Decimal("0.30")
    assert difference(Decimal("999999999999999999999999999999.99"), Decimal("0.01")) == Decimal(
        "999999999999999999999999999999.98"
    )
    model = MovementTotals(
        income=Decimal("0.3"), expenses=Decimal("0.10"), net=Decimal("0.20"), entry_count=2
    )
    assert model.model_dump(mode="json")["income"] == "0.30"


@pytest.mark.parametrize(
    "amounts, expected",
    [
        (["1", "1", "1"], ["33.34", "33.33", "33.33"]),
        (["0.1", "0.2"], ["33.33", "66.67"]),
        (["0", "0"], ["0.00", "0.00"]),
        ([], []),
    ],
)
def test_percentage_allocation(amounts, expected):
    values = percentages([Decimal(value) for value in amounts])
    assert [format(value, ".2f") for value in values] == expected
    if amounts and any(Decimal(value) for value in amounts):
        assert sum(values) == Decimal("100.00")


def test_calendar_boundaries():
    assert month_end(date(2024, 2, 1)) == date(2024, 2, 29)
    assert next_month(date(2025, 12, 1)) == date(2026, 1, 1)
    assert resolve_period(date(2026, 1, 1), date(2026, 1, 31)) == (
        date(2026, 1, 1),
        date(2026, 1, 31),
    )


@pytest.mark.parametrize(
    "start,end",
    [
        (date(2026, 1, 1), None),
        (None, date(2026, 1, 1)),
        (date(2026, 2, 1), date(2026, 1, 1)),
        (date(2010, 1, 1), date(2026, 1, 1)),
        (date(1800, 1, 1), date(1800, 2, 1)),
    ],
)
def test_invalid_periods(start, end):
    with pytest.raises(HTTPException) as error:
        resolve_period(start, end)
    assert error.value.status_code == 422
