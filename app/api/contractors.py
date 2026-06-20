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

from contracts.contractor import ContractorProfile
from core.db import get_session
from rag.contractor_context import (
    get_context,
    get_profile,
    list_contractors,
    upsert_contractor,
)

logger = structlog.get_logger()
router = APIRouter()


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
) -> ContractorProfile:
    """Create a new contractor profile."""
    profile = ContractorProfile(id=str(uuid.uuid4())[:8], **body.model_dump())
    await upsert_contractor(profile, session)
    return profile


@router.get("/contractors", response_model=list[ContractorProfile])
async def list_all_contractors(
    session: AsyncSession = Depends(get_session),
) -> list[ContractorProfile]:
    """List all contractor profiles."""
    return await list_contractors(session)


@router.get("/contractors/{contractor_id}", response_model=ContractorProfile)
async def read_contractor(
    contractor_id: str,
    session: AsyncSession = Depends(get_session),
) -> ContractorProfile:
    """Fetch a single contractor profile."""
    profile = await get_profile(contractor_id, session)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Contractor {contractor_id!r} not found")
    return profile


@router.put("/contractors/{contractor_id}", response_model=ContractorProfile)
async def update_contractor(
    contractor_id: str,
    body: ContractorUpdate,
    session: AsyncSession = Depends(get_session),
) -> ContractorProfile:
    """Partially update a contractor profile."""
    profile = await get_profile(contractor_id, session)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Contractor {contractor_id!r} not found")
    updated = profile.model_copy(update=body.model_dump(exclude_unset=True))
    await upsert_contractor(updated, session)
    return updated


@router.get("/contractors/{contractor_id}/context")
async def read_contractor_context(
    contractor_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return the proposal-generation context for a contractor.

    Falls back to default markup/terms for an unknown contractor.
    """
    return await get_context(contractor_id, session)
