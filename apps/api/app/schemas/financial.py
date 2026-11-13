from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

import pycountry
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

EntryType = Literal["income", "expense"]
EntryStatus = Literal["draft", "pending", "paid"]


def exact_date(value):
    if type(value) is date:
        return value
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Use a calendar date in YYYY-MM-DD format")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Use a valid calendar date in YYYY-MM-DD format") from None
    if parsed.isoformat() != value:
        raise ValueError("Use a calendar date in YYYY-MM-DD format")
    return parsed


FinancialDate = Annotated[date, BeforeValidator(exact_date)]


def exact_decimal(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Send decimal values as strings, not floating-point numbers")
    return value


Money = Annotated[
    Decimal,
    BeforeValidator(exact_decimal),
    Field(ge=0, le=Decimal("999999999999.99"), max_digits=14, decimal_places=2),
]
Rate = Annotated[
    Decimal, BeforeValidator(exact_decimal), Field(ge=0, le=100, max_digits=7, decimal_places=4)
]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CategoryCreate(InputModel):
    name: str = Field(min_length=1, max_length=100)
    type: EntryType
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class CategoryUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    active: bool | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def no_null_required(self):
        if ("name" in self.model_fields_set and self.name is None) or (
            "active" in self.model_fields_set and self.active is None
        ):
            raise ValueError("Name and active cannot be null")
        return self


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    type: EntryType
    color: str | None
    active: bool


class EntryCreate(InputModel):
    title: str = Field(min_length=1, max_length=200)
    amount: Money = Field(gt=0)
    currency: str = "EUR"
    country: str = "BE"
    category_id: UUID | None = None
    counterparty: str | None = Field(default=None, max_length=200)
    entry_date: FinancialDate = Field(default_factory=date.today)
    payment_date: FinancialDate | None = None
    status: EntryStatus = "draft"
    vat_rate: Rate = Decimal("0")
    vat_amount: Money | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value):
        if pycountry.currencies.get(alpha_3=value) is None:
            raise ValueError("Use an uppercase ISO 4217 currency code")
        return value

    @field_validator("country")
    @classmethod
    def valid_country(cls, value):
        if pycountry.countries.get(alpha_2=value) is None:
            raise ValueError("Use an uppercase ISO 3166 country code")
        return value

    @model_validator(mode="after")
    def valid_payment(self):
        if self.payment_date is None:
            self.payment_date = self.entry_date
        if self.vat_amount is not None and self.vat_amount > self.amount:
            raise ValueError("VAT amount cannot exceed the total")
        if self.status == "paid" and self.payment_date > date.today():
            raise ValueError("An actual payment date cannot be in the future")
        return self


class EntryUpdate(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Money | None = Field(default=None, gt=0)
    currency: str | None = None
    country: str | None = None
    category_id: UUID | None = None
    counterparty: str | None = Field(default=None, max_length=200)
    entry_date: FinancialDate | None = None
    payment_date: FinancialDate | None = None
    status: EntryStatus | None = None
    vat_rate: Rate | None = None
    vat_amount: Money | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def no_null_required(self):
        required = {
            "title",
            "amount",
            "currency",
            "country",
            "entry_date",
            "payment_date",
            "status",
            "vat_rate",
        }
        if any(getattr(self, key) is None for key in self.model_fields_set & required):
            raise ValueError("Required entry fields cannot be null")
        return self


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: EntryType
    title: str
    amount: Decimal
    amount_excluding_vat: Decimal
    currency: str
    country: str
    category_id: UUID | None
    category: CategoryOut | None
    counterparty: str | None
    entry_date: date
    payment_date: date
    status: EntryStatus
    vat_rate: Decimal
    vat_amount: Decimal
    vat_overridden: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("amount", "vat_amount", "amount_excluding_vat")
    def money_string(self, value: Decimal) -> str:
        return format(value, ".2f")

    @field_serializer("vat_rate")
    def rate_string(self, value: Decimal) -> str:
        return format(value, ".4f")


class EntryPage(BaseModel):
    items: list[EntryOut]
    total: int
    page: int
    page_size: int
