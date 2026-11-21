"""Alembic environment, configured from app.config and the SQLModel metadata.

The database URL comes from `sqlalchemy.url` when a caller sets it (tests),
otherwise from the application settings (`DATABASE_URL`).

Migrations run on a plain connection, without `PRAGMA foreign_keys = ON`:
SQLite batch migrations recreate tables, and enforcing foreign keys while a
table is dropped and copied would cascade deletes or fail. The application
engine (app.db) turns foreign keys on for every normal connection.
"""

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers every table on SQLModel.metadata)
from app.config import get_settings
from app.db import ensure_sqlite_dir

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata


def database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


# Indexes on expressions (here `name COLLATE NOCASE`) cannot be reflected on SQLite,
# so autogenerate would report them as changed on every run. They are written by
# hand in the migrations and left out of the comparison.
HAND_WRITTEN_INDEXES = {"ix_counterparty_name"}


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    return not (type_ == "index" and name in HAND_WRITTEN_INDEXES)


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    """Render our TypeDecorators as their plain SQL type (sa.Text(), sa.Integer()),
    so migration files never import application code."""
    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        render_item=render_item,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = database_url()
    ensure_sqlite_dir(url)
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            render_item=render_item,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
