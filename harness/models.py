"""ORM models for persisting Envelopes and Contractors to the database."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from contracts.contractor import ContractorProfile
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
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
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
            owner_id=envelope.owner_id,
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
        self.owner_id = envelope.owner_id
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
    owner_id: str | None = None,
    limit: int = 20,
) -> list[Envelope]:
    """List envelopes, optionally filtered by status and/or owner."""
    stmt = select(EnvelopeRow).order_by(EnvelopeRow.updated_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(EnvelopeRow.status == status)
    if owner_id is not None:
        stmt = stmt.where(EnvelopeRow.owner_id == owner_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [r.to_domain() for r in rows]


class ContractorRow(Base):
    __tablename__ = "contractors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    @classmethod
    def from_domain(cls, profile: ContractorProfile) -> ContractorRow:
        now = datetime.now(UTC)
        return cls(
            id=profile.id,
            name=profile.name,
            company=profile.company,
            owner_id=profile.owner_id,
            created_at=now,
            updated_at=now,
            profile_json=profile.model_dump_json(),
        )

    def to_domain(self) -> ContractorProfile:
        return ContractorProfile.model_validate(json.loads(self.profile_json))

    def sync_from_domain(self, profile: ContractorProfile) -> None:
        self.name = profile.name
        self.company = profile.company
        self.owner_id = profile.owner_id
        self.updated_at = datetime.now(UTC)
        self.profile_json = profile.model_dump_json()


async def save_contractor(profile: ContractorProfile, session: AsyncSession) -> None:
    """Upsert a contractor profile to the database."""
    existing = await session.get(ContractorRow, profile.id)
    if existing is None:
        session.add(ContractorRow.from_domain(profile))
    else:
        existing.sync_from_domain(profile)
    await session.commit()


async def load_contractor(contractor_id: str, session: AsyncSession) -> ContractorProfile | None:
    """Load a contractor profile by ID, returning None if not found."""
    row = await session.get(ContractorRow, contractor_id)
    if row is None:
        return None
    return row.to_domain()


async def list_contractor_profiles(
    session: AsyncSession, *, owner_id: str | None = None, limit: int = 100
) -> list[ContractorProfile]:
    """List contractor profiles, most recently updated first, optionally by owner."""
    stmt = select(ContractorRow).order_by(ContractorRow.updated_at.desc()).limit(limit)
    if owner_id is not None:
        stmt = stmt.where(ContractorRow.owner_id == owner_id)
    result = await session.execute(stmt)
    return [r.to_domain() for r in result.scalars().all()]
