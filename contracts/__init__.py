"""
contracts — Typed data contracts for all inter-agent communication.

Every piece of data that crosses an agent boundary MUST be represented
as one of these contract types.  The validation gate enforces conformance
at pipeline seams.  If data doesn't fit a contract, fix the producer —
never loosen the contract to match bad data.
"""

from contracts.classifier import ClassificationResult, QuoteFormat
from contracts.contractor import ContractorProfile
from contracts.envelope import Envelope, EnvelopeStatus
from contracts.errors import (
    BudgetExceededError,
    ContextWindowExceededError,
    ContractViolation,
    ExtractionError,
    PolicyViolationError,
    ValidationError,
)
from contracts.events import DomainEvent, EventKind
from contracts.extraction import (
    ExtractionResult,
    HeaderData,
    LineItem,
    TotalsData,
)
from contracts.review import ReviewDecision, ReviewVerdict

__all__ = [
    "Envelope",
    "EnvelopeStatus",
    "LineItem",
    "ExtractionResult",
    "HeaderData",
    "TotalsData",
    "ClassificationResult",
    "QuoteFormat",
    "ContractorProfile",
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
