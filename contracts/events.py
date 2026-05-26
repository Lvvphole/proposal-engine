"""Domain events emitted as an envelope moves through the pipeline.

Events are append-only.  They form the audit trail and feed the
observability / instrumentation layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class EventKind(StrEnum):
    RECEIVED = "received"
    CLASSIFIED = "classified"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"
    EXTRACTION_FAILED = "extraction_failed"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    RECOVERY_SUCCEEDED = "recovery_succeeded"
    RECOVERY_EXHAUSTED = "recovery_exhausted"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    PROPOSAL_GENERATED = "proposal_generated"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"


class DomainEvent(BaseModel):
    """A single event in an envelope's lifecycle."""

    kind: EventKind
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: str = Field(..., description="Which agent/component emitted this event")
    detail: str = ""
    metadata: dict = Field(default_factory=dict)
