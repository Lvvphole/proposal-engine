"""Contractor management API.

CRUD endpoints for contractor profiles — the preferences (markup, payment
terms, branding) that drive proposal generation.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import Principal, get_current_principal, tenancy_owner
from contracts.contractor import ContractorProfile
from core.db import get_session
from rag.contractor_context import (
    get_profile,
    list_contractors,
    upsert_contractor,
)

logger = structlog.get_logger()
router = APIRouter()


async def _owned_contractor(
    contractor_id: str, session: AsyncSession, principal: Principal
) -> ContractorProfile:
    """Load a contractor, 404-ing if missing or owned by another user."""
    profile = await get_profile(contractor_id, session)
    owner = tenancy_owner(principal)
    if profile is None or (owner is not None and profile.owner_id != owner):
        raise HTTPException(status_code=404, detail=f"Contractor {contractor_id!r} not found")
    return profile


class ContractorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    company: str = ""
    default_markup_pct: float = Field(0.20, ge=0.0, le=1.0)
    category_markups: dict[str, float] = Field(default_factory=dict)
    payment_terms: str = "Due on completion"
    license_number: str = ""
    phone: str = ""
    email: str = ""
    branding: dict[str, Any] = Field(default_factory=dict)


class ContractorUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    default_markup_pct: float | None = Field(None, ge=0.0, le=1.0)
    category_markups: dict[str, float] | None = None
    payment_terms: str | None = None
    license_number: str | None = None
    phone: str | None = None
    email: str | None = None
    branding: dict[str, Any] | None = None


@router.post("/contractors", response_model=ContractorProfile, status_code=201)
async def create_contractor(
    body: ContractorCreate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> ContractorProfile:
    """Create a new contractor profile."""
    profile = ContractorProfile(
        id=str(uuid.uuid4())[:8], owner_id=tenancy_owner(principal), **body.model_dump()
    )
    await upsert_contractor(profile, session)
    return profile


@router.get("/contractors", response_model=list[ContractorProfile])
async def list_all_contractors(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> list[ContractorProfile]:
    """List the caller's contractor profiles."""
    return await list_contractors(session, owner_id=tenancy_owner(principal))


@router.get("/contractors/{contractor_id}", response_model=ContractorProfile)
async def read_contractor(
    contractor_id: str,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> ContractorProfile:
    """Fetch a single contractor profile."""
    return await _owned_contractor(contractor_id, session, principal)


@router.put("/contractors/{contractor_id}", response_model=ContractorProfile)
async def update_contractor(
    contractor_id: str,
    body: ContractorUpdate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> ContractorProfile:
    """Partially update a contractor profile."""
    profile = await _owned_contractor(contractor_id, session, principal)
    # Only apply fields the client actually set, and drop explicit nulls —
    # the profile's fields are non-nullable, so a null would corrupt the row.
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    # Re-validate the merged result rather than copying unchecked (owner_id is
    # preserved via the existing profile's dump).
    updated = ContractorProfile.model_validate({**profile.model_dump(), **changes})
    await upsert_contractor(updated, session)
    return updated


@router.get("/contractors/{contractor_id}/context")
async def read_contractor_context(
    contractor_id: str,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    """Return the proposal-generation context for a contractor.

    Falls back to default markup/terms for an unknown or unowned contractor
    (so it never leaks another user's pricing).
    """
    owner = tenancy_owner(principal)
    profile = await get_profile(contractor_id, session)
    if profile is not None and (owner is None or profile.owner_id == owner):
        return profile.to_context()
    return ContractorProfile(id=contractor_id, name="(unknown)").to_context()
