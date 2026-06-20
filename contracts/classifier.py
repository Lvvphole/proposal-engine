"""Classification contracts.

The classifier agent inspects inbound documents and determines:
1. What format the quote is in (structured table, semi-structured, free-text)
2. Which extraction pipeline should handle it
3. Confidence in the classification
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field


class QuoteFormat(StrEnum):
    """The three canonical quote formats we handle."""

    STRUCTURED_TABLE = "structured_table"  # Pipeline A: clean tabular data
    SEMI_STRUCTURED = "semi_structured"  # Pipeline B: mixed layout
    UNSTRUCTURED_FREETEXT = "unstructured"  # Pipeline C: free-form text/images


class ClassificationResult(BaseModel):
    """Output of the classifier agent."""

    format: QuoteFormat
    pipeline: str = Field(
        ...,
        pattern=r"^(a|b|c)$",
        description="Target pipeline identifier",
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    reasoning: str = Field(..., max_length=500)
    detected_supplier: str | None = None
    page_count: int | None = None
    has_images: bool = False

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.85

    @property
    def needs_fallback(self) -> bool:
        return self.confidence < 0.5
