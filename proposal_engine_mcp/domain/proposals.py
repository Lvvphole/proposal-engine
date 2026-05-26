"""Proposal domain models for MCP server."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ProposalSummary(BaseModel):
    """Summary view of a proposal."""

    envelope_id: str
    status: str
    supplier_name: str = ""
    line_item_count: int = 0
    total_amount: str = "0.00"
    created_at: datetime | None = None
    confidence: float = 0.0


class ProposalDetail(BaseModel):
    """Full proposal with extraction results."""

    envelope_id: str
    status: str
    supplier_name: str = ""
    header: dict = Field(default_factory=dict)
    line_items: list[dict] = Field(default_factory=list)
    totals: dict = Field(default_factory=dict)
    markup_applied: bool = False
    contractor_total: str = "0.00"
    quality_score: float = 0.0
