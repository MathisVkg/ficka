from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("type", "name_key", name="uq_categories_type_name_key"),
        CheckConstraint("type IN ('income', 'expense')", name="ck_categories_type"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    name_key: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(10))
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Entry(Base):
    __tablename__ = "financial_entries"
    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name="ck_entries_type"),
        CheckConstraint("status IN ('draft', 'pending', 'paid')", name="ck_entries_status"),
        CheckConstraint("amount > 0", name="ck_entries_positive_amount"),
        CheckConstraint("vat_rate >= 0 AND vat_rate <= 100", name="ck_entries_vat_rate"),
        CheckConstraint("vat_amount >= 0 AND vat_amount <= amount", name="ck_entries_vat_amount"),
        Index("ix_entries_type_deleted_date", "type", "deleted_at", "entry_date"),
        Index("ix_entries_category", "category_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    type: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    country: Mapped[str] = mapped_column(String(2), default="BE")
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
    )
    category: Mapped[Category | None] = relationship(lazy="selectin")
    counterparty: Mapped[str | None] = mapped_column(String(200), nullable=True)
    entry_date: Mapped[date] = mapped_column(Date)
    payment_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="draft")
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("0"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    vat_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def amount_excluding_vat(self) -> Decimal:
        return self.amount - self.vat_amount
