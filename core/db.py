"""Database setup and session management.

Uses SQLAlchemy's async engine.  All ORM models inherit from the
``Base`` defined here.  Schema is managed by Alembic (see ``migrations/``);
``init_db`` is a convenience for local dev / tests only.

The configured ``DATABASE_URL`` is normalised to an async driver:

  - ``sqlite://``        -> ``sqlite+aiosqlite://``
  - ``postgres[ql]://``  -> ``postgresql+asyncpg://``  (Supabase, RDS, ...)

Supabase connection strings request TLS via a libpq ``?sslmode=require``
query parameter, which asyncpg does not understand.  We strip it and request
TLS through ``connect_args`` instead.
"""

from __future__ import annotations

import ssl
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import get_config


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_require_ssl = False

# Supabase serves Postgres from these domains (direct + connection pooler).
_SUPABASE_HOSTS = (".supabase.co", ".supabase.com")


def _make_url() -> str:
    """Normalise ``DATABASE_URL`` to an async driver URL.

    Side effect: sets the module-level ``_require_ssl`` flag when the target
    requires TLS, so ``_get_engine`` can wire up an SSL context for asyncpg.
    """
    global _require_ssl
    url = get_config().database_url

    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if url.startswith("postgresql+asyncpg://"):
        parts = urlsplit(url)
        pairs = parse_qsl(parts.query)
        sslmode = dict(pairs).get("sslmode")
        host = parts.hostname or ""
        if (sslmode and sslmode != "disable") or any(
            host.endswith(suffix) for suffix in _SUPABASE_HOSTS
        ):
            _require_ssl = True
        # asyncpg rejects libpq-only query params; drop them.
        clean = [(k, v) for k, v in pairs if k not in ("sslmode", "channel_binding")]
        url = urlunsplit(parts._replace(query=urlencode(clean)))

    return url


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        config = get_config()
        url = _make_url()
        connect_args: dict[str, Any] = {}
        if _require_ssl:
            connect_args["ssl"] = ssl.create_default_context()
        _engine = create_async_engine(url, echo=config.debug, connect_args=connect_args)
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


def reset_engine() -> None:
    """Discard the cached engine and session factory. Used in tests to swap DB URLs."""
    global _engine, _session_factory, _require_ssl
    _engine = None
    _session_factory = None
    _require_ssl = False


async def get_session() -> AsyncSession:  # type: ignore[misc]
    async with _get_session_factory()() as session:
        yield session


def _register_models() -> None:
    """Import all ORM model modules so their tables are registered on
    ``Base.metadata`` before ``create_all`` runs. Without this, table
    creation depends on import order."""
    import harness.models  # noqa: F401


async def init_db() -> None:
    """Create all tables.  For dev/test only — production uses Alembic."""
    _register_models()
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
