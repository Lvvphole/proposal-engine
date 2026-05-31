"""
contracts — Typed data contracts for all inter-agent communication.

Every piece of data that crosses an agent boundary MUST be represented
as one of these contract types.  The validation gate enforces conformance
at pipeline seams.  If data doesn't fit a contract, fix the producer —
never loosen the contract to match bad data.
"""

from contracts.envelope import Envelope, EnvelopeStatus
from contracts.extraction import (
    LineItem,
    ExtractionResult,
    HeaderData,
    TotalsData,
)
from contracts.classifier import ClassificationResult, QuoteFormat
from contracts.review import ReviewDecision, ReviewVerdict
from contracts.errors import (
    ContractViolation,
    ExtractionError,
    ValidationError,
    BudgetExceededError,
    PolicyViolationError,
    ContextWindowExceededError,
)
from contracts.events import DomainEvent, EventKind

__all__ = [
    "Envelope",
    "EnvelopeStatus",
    "LineItem",
    "ExtractionResult",
    "HeaderData",
    "TotalsData",
    "ClassificationResult",
    "QuoteFormat",
    "ReviewDecision",
    "ReviewVerdict",
    "ContractViolation",
    "ExtractionError",
    "ValidationError",
    "BudgetExceededError",
    "PolicyViolationError",
    "ContextWindowExceededError",
    "DomainEvent",
    "EventKind",
]
