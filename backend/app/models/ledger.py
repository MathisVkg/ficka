"""4. Ledger: entries, lines, payments."""

import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Index, Integer, Text, text
from sqlmodel import SQLModel

from app.models.base import (
    BoolInt,
    DateText,
    StrEnumText,
    UtcTimestamp,
    bool_check,
    column,
    created_at_column,
    enum_check,
    id_column,
    range_check,
    updated_at_column,
)
from app.models.reference import Direction


class EntryStatus(enum.StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"


class EntrySource(enum.StrEnum):
    MANUAL = "manual"
    RECURRING = "recurring"
    DOCUMENT = "document"
    BANK = "bank"


class PaymentSource(enum.StrEnum):
    MANUAL = "manual"
    ASSUMED = "assumed"
    BANK = "bank"


class Entry(SQLModel, table=True):
    __tablename__ = "entry"
    __table_args__ = (
        enum_check("direction", Direction),
        enum_check("status", EntryStatus),
        enum_check("source", EntrySource),
        bool_check("amounts_include_vat"),
        CheckConstraint("due_date IS NULL OR due_date >= invoice_date", name="due_date"),
        CheckConstraint(
            "structured_reference IS NULL OR length(structured_reference) = 12",
            name="structured_reference",
        ),
        CheckConstraint("total_gross_cents = total_net_cents + total_vat_cents", name="totals"),
        CheckConstraint("(status = 'confirmed') = (confirmed_at IS NOT NULL)", name="confirmed_at"),
        Index("ix_entry_company_date", "company_id", "invoice_date"),
        Index("ix_entry_company_status", "company_id", "status"),
        Index("ix_entry_counterparty", "counterparty_id"),
        Index(
            "ix_entry_document_hash",
            "company_id",
            "document_hash",
            sqlite_where=text("document_hash IS NOT NULL"),
        ),
        Index(
            "ix_entry_invoice_number",
            "company_id",
            "counterparty_id",
            "invoice_number",
            sqlite_where=text("invoice_number IS NOT NULL"),
        ),
    )

    id: int | None = id_column()
    company_id: int = column(Integer, nullable=False, foreign_key="company.id", ondelete="CASCADE")
    direction: Direction = column(StrEnumText(Direction), nullable=False)
    status: EntryStatus = column(
        StrEnumText(EntryStatus),
        nullable=False,
        server_default="'confirmed'",
        default=EntryStatus.CONFIRMED,
    )
    source: EntrySource = column(
        StrEnumText(EntrySource),
        nullable=False,
        server_default="'manual'",
        default=EntrySource.MANUAL,
    )
    invoice_date: date = column(DateText, nullable=False)
    due_date: date | None = column(DateText, nullable=True)
    counterparty_id: int | None = column(
        Integer, nullable=True, foreign_key="counterparty.id", ondelete="SET NULL"
    )
    # RESTRICT: entries must be reassigned before their category can be deleted.
    category_id: int | None = column(
        Integer, nullable=True, foreign_key="category.id", ondelete="RESTRICT"
    )
    description: str | None = column(Text, nullable=True)
    invoice_number: str | None = column(Text, nullable=True)
    structured_reference: str | None = column(Text, nullable=True)  # 12 digits
    currency: str = column(Text, nullable=False, server_default="'EUR'", default="EUR")
    amounts_include_vat: bool = column(BoolInt, nullable=False, server_default="0", default=False)
    # Cached totals: always recomputed from entry_line by the service layer.
    total_net_cents: int = column(Integer, nullable=False, server_default="0", default=0)
    total_vat_cents: int = column(Integer, nullable=False, server_default="0", default=0)
    total_gross_cents: int = column(Integer, nullable=False, server_default="0", default=0)
    document_hash: str | None = column(Text, nullable=True)  # SHA-256 of the processed file
    document_location: str | None = column(Text, nullable=True)
    confirmed_at: datetime | None = column(UtcTimestamp, nullable=True)
    created_at: datetime = created_at_column()
    updated_at: datetime = updated_at_column()


class EntryLine(SQLModel, table=True):
    __tablename__ = "entry_line"
    __table_args__ = (
        range_check("vat_rate_bp", 0, 10000),
        bool_check("vat_manual"),
        CheckConstraint("vat_rate_bp IS NOT NULL OR vat_cents = 0", name="no_rate_no_vat"),
        Index("ix_entry_line_entry", "entry_id"),
    )

    id: int | None = id_column()
    entry_id: int = column(Integer, nullable=False, foreign_key="entry.id", ondelete="CASCADE")
    position: int = column(Integer, nullable=False, server_default="0", default=0)
    description: str | None = column(Text, nullable=True)
    net_cents: int = column(Integer, nullable=False)
    vat_rate_bp: int | None = column(Integer, nullable=True)  # NULL = no VAT
    vat_cents: int = column(Integer, nullable=False, server_default="0", default=0)
    # True = the user or the document set the VAT amount: do not recalculate.
    vat_manual: bool = column(BoolInt, nullable=False, server_default="0", default=False)


class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_cents"),
        enum_check("source", PaymentSource),
        Index("ix_payment_entry", "entry_id"),
        Index("ix_payment_paid_on", "paid_on"),
    )

    id: int | None = id_column()
    entry_id: int = column(Integer, nullable=False, foreign_key="entry.id", ondelete="CASCADE")
    paid_on: date = column(DateText, nullable=False)
    amount_cents: int = column(Integer, nullable=False)
    source: PaymentSource = column(
        StrEnumText(PaymentSource),
        nullable=False,
        server_default="'manual'",
        default=PaymentSource.MANUAL,
    )
    note: str | None = column(Text, nullable=True)
    created_at: datetime = created_at_column()
