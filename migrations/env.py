"""Alembic migration environment (async).

Reads the database URL from the application config via ``core.db`` so the
same ``DATABASE_URL`` drives the app, tests, and migrations — including the
Supabase asyncpg + TLS normalisation. Run with ``alembic upgrade head``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection

from core.db import Base, _get_engine, _make_url, _register_models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all ORM models so their tables are registered on the metadata.
_register_models()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to the script output without a live connection."""
    context.configure(
        url=_make_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live async engine."""
    engine = _get_engine()
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
