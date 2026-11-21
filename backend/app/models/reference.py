"""3. Reference data: categories and counterparties."""

import enum
from datetime import datetime

from sqlalchemy import Index, Integer, Text, UniqueConstraint, text
from sqlmodel import SQLModel

from app.models.base import (
    BoolInt,
    StrEnumText,
    bool_check,
    column,
    created_at_column,
    enum_check,
    id_column,
    range_check,
    updated_at_column,
)


class Direction(enum.StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class CounterpartyRole(enum.StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    BOTH = "both"


class Category(SQLModel, table=True):
    __tablename__ = "category"
    __table_args__ = (
        enum_check("direction", Direction),
        range_check("default_vat_rate_bp", 0, 10000),
        bool_check("is_seeded"),
        UniqueConstraint("company_id", "direction", "name"),
    )

    id: int | None = id_column()
    company_id: int = column(Integer, nullable=False, foreign_key="company.id", ondelete="CASCADE")
    direction: Direction = column(StrEnumText(Direction), nullable=False)
    name: str = column(Text, nullable=False)
    default_vat_rate_bp: int | None = column(Integer, nullable=True)  # NULL = no VAT
    is_seeded: bool = column(BoolInt, nullable=False, server_default="0", default=False)
    position: int = column(Integer, nullable=False, server_default="0", default=0)
    created_at: datetime = created_at_column()
    updated_at: datetime = updated_at_column()


class Counterparty(SQLModel, table=True):
    __tablename__ = "counterparty"
    __table_args__ = (
        enum_check("role", CounterpartyRole),
        range_check("default_vat_rate_bp", 0, 10000),
        Index(
            "ux_counterparty_vat",
            "company_id",
            "vat_number",
            unique=True,
            sqlite_where=text("vat_number IS NOT NULL"),
        ),
        Index("ix_counterparty_name", "company_id", text("name COLLATE NOCASE")),
    )

    id: int | None = id_column()
    company_id: int = column(Integer, nullable=False, foreign_key="company.id", ondelete="CASCADE")
    name: str = column(Text, nullable=False)
    role: CounterpartyRole = column(
        StrEnumText(CounterpartyRole),
        nullable=False,
        server_default="'supplier'",
        default=CounterpartyRole.SUPPLIER,
    )
    vat_number: str | None = column(Text, nullable=True)  # normalized, e.g. 'BE0123456749'
    default_category_id: int | None = column(
        Integer, nullable=True, foreign_key="category.id", ondelete="SET NULL"
    )
    default_vat_rate_bp: int | None = column(Integer, nullable=True)
    notes: str | None = column(Text, nullable=True)
    created_at: datetime = created_at_column()
    updated_at: datetime = updated_at_column()


class CounterpartyIban(SQLModel, table=True):
    __tablename__ = "counterparty_iban"
    __table_args__ = (
        UniqueConstraint("counterparty_id", "iban"),
        Index("ix_counterparty_iban", "iban"),
    )

    id: int | None = id_column()
    counterparty_id: int = column(
        Integer, nullable=False, foreign_key="counterparty.id", ondelete="CASCADE"
    )
    iban: str = column(Text, nullable=False)  # normalized, no spaces, upper case
