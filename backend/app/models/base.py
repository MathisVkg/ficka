"""Shared building blocks for the SQLModel tables.

Storage conventions (see docs/database.md) are implemented as SQLAlchemy
`TypeDecorator`s, so the database sees exactly the types of `docs/schema.sql`
(TEXT / INTEGER) while Python code works with real values:

| Python value             | Column type      | Stored as                        |
|--------------------------|------------------|----------------------------------|
| `datetime.date`          | `DateText`       | TEXT `YYYY-MM-DD`                |
| aware `datetime` (UTC)   | `UtcTimestamp`   | TEXT `YYYY-MM-DDTHH:MM:SSZ`      |
| `bool`                   | `BoolInt`        | INTEGER 0 / 1                    |
| `StrEnum` member         | `StrEnumText`    | TEXT (+ a CHECK on the values)   |
| money (`int` cents)      | `Integer`        | INTEGER                          |
| VAT rate (`int` bp)      | `Integer`        | INTEGER, NULL = no VAT           |

CHECK, UNIQUE and index definitions go in each model's `__table_args__`.
"""

import enum
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Text, text
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel

# Deterministic constraint names, so Alembic batch migrations on SQLite can
# address constraints later. Index names are always given explicitly.
SQLModel.metadata.naming_convention = {
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    """Current UTC time, truncated to whole seconds (the stored precision)."""
    return datetime.now(UTC).replace(microsecond=0)


def format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Timestamps must be timezone-aware (UTC)")
    return value.astimezone(UTC).strftime(TIMESTAMP_FORMAT)


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, TIMESTAMP_FORMAT).replace(tzinfo=UTC)


class DateText(TypeDecorator[date]):
    """A calendar date stored as TEXT 'YYYY-MM-DD'."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            raise TypeError("DateText expects a date, not a datetime")
        if isinstance(value, str):
            value = date.fromisoformat(value)
        return value.isoformat()

    def process_result_value(self, value: Any, dialect: Any) -> date | None:
        return None if value is None else date.fromisoformat(value)


class UtcTimestamp(TypeDecorator[datetime]):
    """A UTC instant stored as TEXT ISO-8601 'YYYY-MM-DDTHH:MM:SSZ'."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = parse_timestamp(value)
        return format_timestamp(value)

    def process_result_value(self, value: Any, dialect: Any) -> datetime | None:
        return None if value is None else parse_timestamp(value)


class BoolInt(TypeDecorator[bool]):
    """A boolean stored as INTEGER 0 / 1 (paired with an `IN (0, 1)` CHECK)."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> int | None:
        return None if value is None else int(bool(value))

    def process_result_value(self, value: Any, dialect: Any) -> bool | None:
        return None if value is None else bool(value)


class StrEnumText(TypeDecorator[enum.StrEnum]):
    """A `StrEnum` stored as plain TEXT (paired with an `IN (...)` CHECK)."""

    impl = Text
    cache_ok = True

    def __init__(self, enum_class: type[enum.StrEnum]) -> None:
        super().__init__()
        self.enum_class = enum_class

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        return None if value is None else self.enum_class(value).value

    def process_result_value(self, value: Any, dialect: Any) -> enum.StrEnum | None:
        return None if value is None else self.enum_class(value)


def enum_check(column_name: str, enum_class: type[enum.StrEnum]) -> CheckConstraint:
    """`CHECK (column IN ('a', 'b'))`, with the values in declaration order."""
    values = ", ".join(f"'{member.value}'" for member in enum_class)
    return CheckConstraint(f"{column_name} IN ({values})", name=column_name)


def bool_check(column_name: str) -> CheckConstraint:
    return CheckConstraint(f"{column_name} IN (0, 1)", name=column_name)


def range_check(column_name: str, low: int, high: int) -> CheckConstraint:
    return CheckConstraint(f"{column_name} BETWEEN {low} AND {high}", name=column_name)


def column(
    type_: Any,
    *,
    nullable: bool,
    primary_key: bool = False,
    foreign_key: str | None = None,
    ondelete: str | None = None,
    unique: bool = False,
    server_default: str | None = None,
    default: Any = None,
    default_factory: Any = None,
) -> Any:
    """A SQLModel field backed by an explicit SQLAlchemy column.

    `server_default` is raw SQL (`"'EUR'"`, `"0"`), matching the schema's DEFAULT.
    `default` / `default_factory` is the Python-side value for new objects.
    """
    args: list[Any] = [type_]
    if foreign_key is not None:
        args.append(ForeignKey(foreign_key, ondelete=ondelete))
    sa_column = Column(
        *args,
        primary_key=primary_key,
        nullable=nullable,
        unique=unique or None,
        server_default=text(server_default) if server_default is not None else None,
    )
    if default_factory is not None:
        return Field(default_factory=default_factory, sa_column=sa_column)
    return Field(default=default, sa_column=sa_column)


def id_column() -> Any:
    """`id INTEGER PRIMARY KEY` (a rowid alias; SQLite does not add NOT NULL)."""
    return column(Integer, primary_key=True, nullable=True)


def created_at_column() -> Any:
    return column(UtcTimestamp, nullable=False, default_factory=utc_now)


def updated_at_column() -> Any:
    return column(UtcTimestamp, nullable=False, default_factory=utc_now)
