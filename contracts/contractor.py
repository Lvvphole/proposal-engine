"""Contractor profile contract.

A contractor's persisted preferences shape every proposal generated for
them: markup rules (default + per-category overrides), payment terms,
branding, and contact details. This is the canonical contractor type;
the persistence layer (``harness.models.ContractorRow``) and the MCP
domain models both build on it.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContractorProfile(BaseModel):
    """A contractor's configuration for proposal generation."""

    id: str
    name: str
    company: str = ""
    # Owning user (Supabase sub) when auth/tenancy is enabled.
    owner_id: str | None = None
    default_markup_pct: float = Field(0.20, ge=0.0, le=1.0)
    category_markups: dict[str, float] = Field(
        default_factory=dict,
        description="Markup percentage overrides keyed by material category.",
    )
    payment_terms: str = "Due on completion"
    license_number: str = ""
    phone: str = ""
    email: str = ""
    branding: dict[str, Any] = Field(
        default_factory=dict,
        description="Logo URL, colors, header template, etc.",
    )
    history_summary: str = "No prior proposals on file."

    def markup_rules(self) -> dict[str, float]:
        """Resolve markup rules: per-category overrides layered on the default."""
        rules: dict[str, float] = {"default_pct": self.default_markup_pct}
        rules.update(self.category_markups)
        return rules

    def to_context(self) -> dict[str, Any]:
        """Shape consumed by proposal generation and prompt assembly."""
        return {
            "contractor_id": self.id,
            "name": self.name,
            "company": self.company,
            "markup_rules": self.markup_rules(),
            "payment_terms": self.payment_terms,
            "branding": self.branding,
            "history_summary": self.history_summary,
        }
