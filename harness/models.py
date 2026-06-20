"""ORM model for persisting Envelopes to the database."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from contracts.envelope import Envelope
from core.db import Base


class EnvelopeRow(Base):
    __tablename__ = "envelopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contractor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    @classmethod
    def from_domain(cls, envelope: Envelope) -> EnvelopeRow:
        return cls(
            id=envelope.id,
            status=envelope.status,
            created_at=envelope.created_at,
            updated_at=envelope.updated_at,
            source_filename=envelope.source_filename,
            source_content_type=envelope.source_content_type,
            contractor_id=envelope.contractor_id,
            payload_json=envelope.model_dump_json(exclude={"source_bytes_b64"}),
        )

    def to_domain(self) -> Envelope:
        data = json.loads(self.payload_json)
        return Envelope.model_validate(data)

    def sync_from_domain(self, envelope: Envelope) -> None:
        self.status = envelope.status
        self.updated_at = envelope.updated_at
        self.source_filename = envelope.source_filename
        self.source_content_type = envelope.source_content_type
        self.contractor_id = envelope.contractor_id
        self.payload_json = envelope.model_dump_json(exclude={"source_bytes_b64"})


async def save_envelope(envelope: Envelope, session: AsyncSession) -> None:
    """Upsert an envelope to the database."""
    existing = await session.get(EnvelopeRow, envelope.id)
    if existing is None:
        row = EnvelopeRow.from_domain(envelope)
        session.add(row)
    else:
        existing.sync_from_domain(envelope)
    await session.commit()


async def load_envelope(envelope_id: str, session: AsyncSession) -> Envelope | None:
    """Load an envelope by ID, returning None if not found."""
    row = await session.get(EnvelopeRow, envelope_id)
    if row is None:
        return None
    return row.to_domain()


async def list_envelopes(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[Envelope]:
    """List envelopes with optional status filter."""
    stmt = select(EnvelopeRow).order_by(EnvelopeRow.updated_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(EnvelopeRow.status == status)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [r.to_domain() for r in rows]
