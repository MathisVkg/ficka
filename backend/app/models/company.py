"""1. Company, users, settings."""

import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Index, Integer, Text
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
    updated_at_column,
)


class RecurringGenerationTiming(enum.StrEnum):
    FIRST_OF_MONTH = "first_of_month"
    DUE_DATE = "due_date"


class RecurringValidationMode(enum.StrEnum):
    REVIEW = "review"
    AUTOMATIC = "automatic"


class UserRole(enum.StrEnum):
    OWNER = "owner"


class Company(SQLModel, table=True):
    __tablename__ = "company"

    id: int | None = id_column()
    name: str = column(Text, nullable=False)
    country_code: str = column(
        Text, nullable=False, foreign_key="vat_country.code", server_default="'BE'", default="BE"
    )
    vat_number: str | None = column(Text, nullable=True)
    currency: str = column(Text, nullable=False, server_default="'EUR'", default="EUR")
    created_at: datetime = created_at_column()
    updated_at: datetime = updated_at_column()


class CompanySettings(SQLModel, table=True):
    __tablename__ = "company_settings"
    __table_args__ = (
        enum_check("recurring_generation_timing", RecurringGenerationTiming),
        enum_check("recurring_validation_mode", RecurringValidationMode),
        bool_check("amounts_include_vat_default"),
        CheckConstraint("document_ttl_hours > 0", name="document_ttl_hours"),
        CheckConstraint(
            "(starting_balance_cents IS NULL) = (starting_balance_date IS NULL)",
            name="starting_balance",
        ),
    )

    company_id: int | None = column(
        Integer,
        primary_key=True,
        nullable=True,
        foreign_key="company.id",
        ondelete="CASCADE",
    )
    recurring_generation_timing: RecurringGenerationTiming = column(
        StrEnumText(RecurringGenerationTiming),
        nullable=False,
        server_default="'first_of_month'",
        default=RecurringGenerationTiming.FIRST_OF_MONTH,
    )
    recurring_validation_mode: RecurringValidationMode = column(
        StrEnumText(RecurringValidationMode),
        nullable=False,
        server_default="'review'",
        default=RecurringValidationMode.REVIEW,
    )
    amounts_include_vat_default: bool = column(
        BoolInt, nullable=False, server_default="0", default=False
    )
    starting_balance_cents: int | None = column(Integer, nullable=True)
    starting_balance_date: date | None = column(DateText, nullable=True)
    document_ttl_hours: int = column(Integer, nullable=False, server_default="24", default=24)
    locale: str = column(Text, nullable=False, server_default="'en'", default="en")
    updated_at: datetime = updated_at_column()


class AppUser(SQLModel, table=True):
    __tablename__ = "app_user"

    id: int | None = id_column()
    email: str = column(Text(collation="NOCASE"), nullable=False, unique=True)
    password_hash: str = column(Text, nullable=False)  # argon2id
    display_name: str = column(Text, nullable=False)
    created_at: datetime = created_at_column()
    last_login_at: datetime | None = column(UtcTimestamp, nullable=True)


class UserCompany(SQLModel, table=True):
    """Foundation only: v1 has one user, one company, role 'owner'."""

    __tablename__ = "user_company"
    __table_args__ = (enum_check("role", UserRole),)

    user_id: int = column(
        Integer, primary_key=True, nullable=False, foreign_key="app_user.id", ondelete="CASCADE"
    )
    company_id: int = column(
        Integer, primary_key=True, nullable=False, foreign_key="company.id", ondelete="CASCADE"
    )
    role: UserRole = column(
        StrEnumText(UserRole), nullable=False, server_default="'owner'", default=UserRole.OWNER
    )


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_session"
    __table_args__ = (Index("ix_auth_session_user", "user_id"),)

    # Hash of the session token, never the token itself.
    id: str | None = column(Text, primary_key=True, nullable=True)
    user_id: int = column(Integer, nullable=False, foreign_key="app_user.id", ondelete="CASCADE")
    created_at: datetime = created_at_column()
    expires_at: datetime = column(UtcTimestamp, nullable=False)
