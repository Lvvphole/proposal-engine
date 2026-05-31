"""Domain-specific error hierarchy.

Every error that can occur within the extraction / proposal pipeline
has a typed representation here.  Agents raise these; the harness
catches and routes them to the appropriate recovery path.
"""

from __future__ import annotations


class ProposalEngineError(Exception):
    """Base for all proposal-engine errors."""

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ContractViolation(ProposalEngineError):
    """Raised when data fails to satisfy a typed contract at a pipeline boundary."""


class ExtractionError(ProposalEngineError):
    """Raised when an agent cannot extract required data from source material."""


class ValidationError(ProposalEngineError):
    """Raised when extracted data fails validation rules (e.g. totals mismatch)."""


class BudgetExceededError(ProposalEngineError):
    """Raised when a pipeline run would exceed the configured token/cost budget."""


class ClassificationError(ProposalEngineError):
    """Raised when the classifier cannot determine the quote format."""


class RecoveryExhaustedError(ProposalEngineError):
    """Raised when all recovery strategies have been attempted and failed."""


class PolicyViolationError(ProposalEngineError):
    """Raised when an operation is denied by a policy (tool permission, rate limit, etc.)."""


class ContextWindowExceededError(ProposalEngineError):
    """Raised when a document exceeds the model's context window after compression."""
