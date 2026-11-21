"""2. VAT configuration (data, not code)."""

from datetime import date

from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint
from sqlmodel import SQLModel

from app.models.base import DateText, column, id_column, range_check


class VatCountry(SQLModel, table=True):
    __tablename__ = "vat_country"

    code: str | None = column(Text, primary_key=True, nullable=True)  # ISO 3166-1 alpha-2
    name: str = column(Text, nullable=False)


class VatRate(SQLModel, table=True):
    __tablename__ = "vat_rate"
    __table_args__ = (
        range_check("rate_bp", 0, 10000),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="validity"),
        UniqueConstraint("country_code", "rate_bp", "valid_from"),
    )

    id: int | None = id_column()
    country_code: str = column(Text, nullable=False, foreign_key="vat_country.code")
    rate_bp: int = column(Integer, nullable=False)
    label: str = column(Text, nullable=False)
    valid_from: date = column(DateText, nullable=False)
    valid_to: date | None = column(DateText, nullable=True)  # NULL = still valid
