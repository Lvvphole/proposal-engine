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


def _make_engine():
    config = get_config()
    url = config.database_url
    # Convert sqlite:// to sqlite+aiosqlite://
    if url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return create_async_engine(url, echo=config.debug)


engine = _make_engine()
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create all tables.  For dev/test only — production uses Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
