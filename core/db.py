"""Database setup and session management.

Uses SQLAlchemy async engine.  All models use the declarative base
defined here.  Alembic migrations are configured in infra/.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_config


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


_engine = None
_session_factory = None


def _make_url() -> str:
    config = get_config()
    url = config.database_url
    if url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def _get_engine():
    global _engine
    if _engine is None:
        config = get_config()
        _engine = create_async_engine(_make_url(), echo=config.debug)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


def reset_engine() -> None:
    """Discard the cached engine and session factory. Used in tests to swap DB URLs."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def get_session() -> AsyncSession:  # type: ignore[misc]
    async with _get_session_factory()() as session:
        yield session


async def init_db() -> None:
    """Create all tables.  For dev/test only — production uses Alembic."""
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
