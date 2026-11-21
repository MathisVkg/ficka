"""5. Recurring: versioned templates and their occurrences."""

import enum
from datetime import date, datetime

from sqlalchemy import DDL, CheckConstraint, Index, Integer, Text, UniqueConstraint, event
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


class AmountMode(enum.StrEnum):
    FIXED = "fixed"
    VARIABLE = "variable"


class OccurrenceStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    SKIPPED = "skipped"


class RecurringTemplate(SQLModel, table=True):
    __tablename__ = "recurring_template"
    __table_args__ = (
        enum_check("direction", Direction),
        range_check("interval_months", 1, 120),
        range_check("due_day", 1, 31),
        CheckConstraint("max_occurrences IS NULL OR max_occurrences > 0", name="max_occurrences"),
        enum_check("amount_mode", AmountMode),
        bool_check("is_active"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="end_date"),
    )

    id: int | None = id_column()
    company_id: int = column(Integer, nullable=False, foreign_key="company.id", ondelete="CASCADE")
    name: str = column(Text, nullable=False)
    direction: Direction = column(StrEnumText(Direction), nullable=False)
    counterparty_id: int | None = column(
        Integer, nullable=True, foreign_key="counterparty.id", ondelete="SET NULL"
    )
    category_id: int | None = column(
        Integer, nullable=True, foreign_key="category.id", ondelete="RESTRICT"
    )
    description: str | None = column(Text, nullable=True)
    # 1 = monthly, 3 = quarterly, 12 = yearly
    interval_months: int = column(Integer, nullable=False, server_default="1", default=1)
    due_day: int = column(Integer, nullable=False)  # 31 = last day of the month
    start_date: date = column(DateText, nullable=False)
    end_date: date | None = column(DateText, nullable=True)
    max_occurrences: int | None = column(Integer, nullable=True)
    amount_mode: AmountMode = column(
        StrEnumText(AmountMode),
        nullable=False,
        server_default="'fixed'",
        default=AmountMode.FIXED,
    )
    is_active: bool = column(BoolInt, nullable=False, server_default="1", default=True)
    created_at: datetime = created_at_column()
    updated_at: datetime = updated_at_column()


class RecurringTemplateVersion(SQLModel, table=True):
    """A price change creates a new version; past occurrences keep theirs."""

    __tablename__ = "recurring_template_version"
    __table_args__ = (UniqueConstraint("template_id", "effective_from"),)

    id: int | None = id_column()
    template_id: int = column(
        Integer, nullable=False, foreign_key="recurring_template.id", ondelete="CASCADE"
    )
    effective_from: date = column(DateText, nullable=False)
    created_at: datetime = created_at_column()


class RecurringTemplateLine(SQLModel, table=True):
    __tablename__ = "recurring_template_line"
    __table_args__ = (
        range_check("vat_rate_bp", 0, 10000),
        Index("ix_template_line_version", "version_id"),
    )

    id: int | None = id_column()
    version_id: int = column(
        Integer, nullable=False, foreign_key="recurring_template_version.id", ondelete="CASCADE"
    )
    position: int = column(Integer, nullable=False, server_default="0", default=0)
    description: str | None = column(Text, nullable=True)
    net_cents: int = column(Integer, nullable=False)
    vat_rate_bp: int | None = column(Integer, nullable=True)  # NULL = no VAT


class RecurringOccurrence(SQLModel, table=True):
    """One row per (template, period): the idempotency guard."""

    __tablename__ = "recurring_occurrence"
    __table_args__ = (
        enum_check("status", OccurrenceStatus),
        UniqueConstraint("template_id", "period"),
        CheckConstraint(
            "status <> 'generated' OR (generated_at IS NOT NULL AND entry_id IS NOT NULL)",
            name="generated",
        ),
        Index("ix_occurrence_due", "status", "due_date"),
    )

    id: int | None = id_column()
    template_id: int = column(
        Integer, nullable=False, foreign_key="recurring_template.id", ondelete="CASCADE"
    )
    version_id: int = column(Integer, nullable=False, foreign_key="recurring_template_version.id")
    period: str = column(Text, nullable=False)  # 'YYYY-MM' of the due date
    due_date: date = column(DateText, nullable=False)
    status: OccurrenceStatus = column(
        StrEnumText(OccurrenceStatus),
        nullable=False,
        server_default="'pending'",
        default=OccurrenceStatus.PENDING,
    )
    entry_id: int | None = column(
        Integer, nullable=True, unique=True, foreign_key="entry.id", ondelete="SET NULL"
    )
    generated_at: datetime | None = column(UtcTimestamp, nullable=True)


# Deleting a generated entry marks its occurrence as skipped, so it is never
# regenerated. The Alembic migration creates the same trigger; this listener
# only covers `metadata.create_all()` (for example in throwaway databases).
TRIGGER_ENTRY_DELETE_SKIPS_OCCURRENCE = """
CREATE TRIGGER trg_entry_delete_skips_occurrence
BEFORE DELETE ON entry
BEGIN
    UPDATE recurring_occurrence SET status = 'skipped', entry_id = NULL WHERE entry_id = OLD.id;
END
"""

event.listen(
    RecurringOccurrence.__table__,  # type: ignore[attr-defined]
    "after_create",
    DDL(TRIGGER_ENTRY_DELETE_SKIPS_OCCURRENCE),
)
