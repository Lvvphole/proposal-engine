"""Review contracts — the human-in-the-loop decision surface.

No proposal is ever auto-sent.  The review surface presents extracted
data + generated proposal to a human reviewer, who makes one of these
decisions.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReviewVerdict(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_EDIT = "needs_edit"
    ESCALATED = "escalated"


class ReviewDecision(BaseModel):
    """A human reviewer's decision on a proposal."""

    envelope_id: str
    verdict: ReviewVerdict
    reviewer_id: str
    notes: str = ""
    edits: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value edits the reviewer made to the proposal",
    )

    @property
    def is_terminal(self) -> bool:
        return self.verdict in (ReviewVerdict.APPROVED, ReviewVerdict.REJECTED)
