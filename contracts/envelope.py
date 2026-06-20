"""Envelope — the unit of work flowing through the system.

Every supplier quote entering the system gets wrapped in an Envelope.
The envelope tracks the document through classification → extraction →
validation → proposal generation → review, accumulating state and
audit events at each stage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from contracts.classifier import ClassificationResult
from contracts.events import DomainEvent
from contracts.extraction import ExtractionResult
from contracts.proposal import Proposal


class EnvelopeStatus(StrEnum):
    RECEIVED = "received"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    REVIEW_PENDING = "review_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class Envelope(BaseModel):
    """Tracks a single quote through the full pipeline."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: EnvelopeStatus = EnvelopeStatus.RECEIVED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Owning user (Supabase sub) when auth/tenancy is enabled.
    owner_id: str | None = None

    # Source material
    source_filename: str | None = None
    source_content_type: str | None = None
    source_bytes_b64: str | None = Field(None, exclude=True)  # excluded from serialization

    # Pipeline outputs (populated as the envelope moves through stages)
    classification: ClassificationResult | None = None
    extraction: ExtractionResult | None = None
    proposal: Proposal | None = None

    # Contractor context
    contractor_id: str | None = None
    contractor_markup_pct: float | None = None

    # Audit trail
    events: list[DomainEvent] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)

    def advance(self, new_status: EnvelopeStatus, event: DomainEvent) -> None:
        """Move the envelope to a new status and record the event."""
        self.status = new_status
        self.updated_at = datetime.now(UTC)
        self.events.append(event)

    @property
    def total_tokens(self) -> int:
        return sum(self.token_usage.values())
