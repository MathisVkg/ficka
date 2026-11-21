"""7. Notifications and app state."""

import enum
from datetime import datetime

from sqlalchemy import Index, Integer, Text
from sqlmodel import SQLModel

from app.models.base import (
    StrEnumText,
    UtcTimestamp,
    column,
    created_at_column,
    enum_check,
    id_column,
    updated_at_column,
)


class NotificationKind(enum.StrEnum):
    RECURRING_PROPOSALS = "recurring_proposals"
    RECURRING_AUTO_CREATED = "recurring_auto_created"
    DOCUMENT_READY = "document_ready"
    DOCUMENT_FAILED = "document_failed"
    DOCUMENT_EXPIRED = "document_expired"


class Notification(SQLModel, table=True):
    """Events worth telling the user once. Badges are computed live, never stored."""

    __tablename__ = "notification"
    __table_args__ = (
        enum_check("kind", NotificationKind),
        Index("ix_notification_unread", "company_id", "read_at"),
    )

    id: int | None = id_column()
    company_id: int = column(Integer, nullable=False, foreign_key="company.id", ondelete="CASCADE")
    kind: NotificationKind = column(StrEnumText(NotificationKind), nullable=False)
    payload_json: str | None = column(Text, nullable=True)
    read_at: datetime | None = column(UtcTimestamp, nullable=True)
    created_at: datetime = created_at_column()


class AppState(SQLModel, table=True):
    """Key/value state for background jobs, e.g. 'recurring.last_run_at'."""

    __tablename__ = "app_state"

    key: str | None = column(Text, primary_key=True, nullable=True)
    value: str = column(Text, nullable=False)
    updated_at: datetime = updated_at_column()
