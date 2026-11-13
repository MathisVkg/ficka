from alembic import context
from sqlalchemy import create_engine, pool, text

from app import models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=get_settings().connection_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(get_settings().connection_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        # Session-level lock serializes migration processes, including version-table setup.
        connection.execute(text("SET lock_timeout = '60s'"))
        connection.execute(text("SELECT pg_advisory_lock(7062302)"))
        connection.commit()
        try:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
        finally:
            if connection.in_transaction():
                connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(7062302)"))
            connection.commit()
    engine.dispose()
