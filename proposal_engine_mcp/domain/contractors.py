"""Contractor domain models for MCP server."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContractorProfile(BaseModel):
    """A contractor's configuration for proposal generation."""

    id: str
    name: str
    company: str = ""
    default_markup_pct: float = Field(0.20, ge=0.0, le=1.0)
    payment_terms: str = "Due on completion"
    license_number: str = ""
    phone: str = ""
    email: str = ""

    # Markup overrides by material category
    category_markups: dict[str, float] = Field(default_factory=dict)


class ContractorSummary(BaseModel):
    """Lightweight view for listing contractors."""

    id: str
    name: str
    company: str
    proposal_count: int = 0
