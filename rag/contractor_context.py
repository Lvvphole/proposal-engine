"""Contractor preference engine.

Loads and persists contractor-specific preferences that shape proposal
generation:

  - Default markup percentage + per-category overrides
  - Payment terms
  - Branding / header templates
  - Prior-proposal history summary

Profiles are persisted in the database (``contractors`` table) so they
survive restarts and are shared across the API and MCP server. ``get_context``
returns the shape consumed by proposal generation and prompt assembly, falling
back to sensible defaults for an unknown contractor.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.contractor import ContractorProfile
from harness.models import (
    list_contractor_profiles,
    load_contractor,
    save_contractor,
)

logger = structlog.get_logger()


async def upsert_contractor(profile: ContractorProfile, session: AsyncSession) -> ContractorProfile:
    """Create or update a contractor profile."""
    await save_contractor(profile, session)
    logger.info("contractor_upserted", contractor_id=profile.id)
    return profile


async def get_profile(contractor_id: str, session: AsyncSession) -> ContractorProfile | None:
    """Return the stored profile, or None if the contractor is unknown."""
    return await load_contractor(contractor_id, session)


async def get_context(contractor_id: str, session: AsyncSession) -> dict[str, Any]:
    """Retrieve contractor context for proposal generation.

    Returns a dict with keys: contractor_id, name, company, markup_rules,
    payment_terms, branding, history_summary. Falls back to default markup
    and terms when the contractor is not on file.
    """
    profile = await load_contractor(contractor_id, session)
    if profile is None:
        profile = ContractorProfile(id=contractor_id, name="(unknown)")
    return profile.to_context()


async def list_contractors(
    session: AsyncSession, *, owner_id: str | None = None
) -> list[ContractorProfile]:
    """List stored contractor profiles, optionally scoped to an owner."""
    return await list_contractor_profiles(session, owner_id=owner_id)
