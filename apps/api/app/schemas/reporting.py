from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, PlainSerializer

Money = Annotated[Decimal, PlainSerializer(lambda value: format(value, ".2f"), return_type=str)]


class PeriodReport(BaseModel):
    currency: Literal["EUR"] = "EUR"
    date_from: date
    date_to: date
    date_basis: Literal["payment_date", "entry_date"] = "payment_date"
    non_eur_excluded_count: int = 0


class MovementTotals(BaseModel):
    income: Money
    expenses: Money
    net: Money
    entry_count: int


class RecordedVat(BaseModel):
    output: Money
    input: Money
    difference: Money
    entry_count: int
    date_basis: Literal["entry_date"] = "entry_date"
    included_statuses: list[str] = ["pending", "paid"]
    non_eur_excluded_count: int = 0


class SummaryReport(PeriodReport):
    actual: MovementTotals
    expected: MovementTotals
    vat: RecordedVat


class CashBucket(BaseModel):
    bucket_start: date
    date_from: date
    date_to: date
    income: Money
    expenses: Money
    net: Money
    entry_count: int


class CashFlowReport(PeriodReport):
    grouping: Literal["month", "week"]
    basis: Literal["actual", "expected"]
    entry_count: int
    items: list[CashBucket]


class CategoryTotal(BaseModel):
    id: UUID | None
    name: str
    color: str | None
    active: bool | None
    amount: Money
    percentage: Money
    entry_count: int


class CategoryReport(PeriodReport):
    type: Literal["income", "expense"]
    total: Money
    entry_count: int
    items: list[CategoryTotal]


class PendingMovement(BaseModel):
    id: UUID
    type: Literal["income", "expense"]
    title: str
    amount: Money
    currency: Literal["EUR"] = "EUR"
    payment_date: date
    overdue: bool


class PendingReport(BaseModel):
    currency: Literal["EUR"] = "EUR"
    scope: Literal["period", "all"]
    date_from: date | None
    date_to: date | None
    date_basis: Literal["payment_date"] = "payment_date"
    as_of: date
    income: Money
    expenses: Money
    net: Money
    total: int
    overdue_count: int
    non_eur_excluded_count: int
    page: int
    page_size: int
    items: list[PendingMovement]


class VatQuarter(BaseModel):
    quarter: int
    date_from: date
    date_to: date
    output: Money
    input: Money
    difference: Money
    entry_count: int


class VatReport(PeriodReport):
    date_basis: Literal["entry_date"] = "entry_date"
    included_statuses: list[str] = ["pending", "paid"]
    year: int
    output: Money
    input: Money
    difference: Money
    entry_count: int
    quarters: list[VatQuarter]
