"""Supplier domain models for MCP server."""

from __future__ import annotations

from pydantic import BaseModel


class SupplierInfo(BaseModel):
    """Supplier catalog entry."""

    name: str
    preferred_pipeline: str = "c"
    extraction_count: int = 0
    avg_accuracy: float = 0.0
    notes: str = ""


class SupplierQuoteSubmission(BaseModel):
    """A supplier quote submitted for processing."""

    filename: str
    content_type: str = "application/pdf"
    content_b64: str
    contractor_id: str | None = None
