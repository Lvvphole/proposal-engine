"""Contractor domain models for MCP server.

``ContractorProfile`` is the canonical contract defined in
``contracts.contractor`` and re-exported here for convenience.
"""

from __future__ import annotations

from pydantic import BaseModel

from contracts.contractor import ContractorProfile

__all__ = ["ContractorProfile", "ContractorSummary"]


class ContractorSummary(BaseModel):
    """Lightweight view for listing contractors."""

    id: str
    name: str
    company: str
    proposal_count: int = 0
