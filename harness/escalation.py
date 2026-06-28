"""Escalation routing for terminal pipeline failures.

Recovery (retry via the Pipeline C fallback) is handled upstream in the
orchestrator. By the time a failure reaches here it is terminal: the envelope
could not be extracted, so there is no proposal to review. Escalation moves it
to the terminal ``FAILED`` state with the appropriate event and surfaces it on
the bus — it never returns the envelope to a transient processing state (doing
so previously left failed quotes stranded in ``extracting`` forever).
"""

from __future__ import annotations

import structlog

from contracts.envelope import Envelope, EnvelopeStatus
from contracts.errors import BudgetExceededError, RecoveryExhaustedError
from contracts.events import DomainEvent, EventKind
from core import message_bus

logger = structlog.get_logger()


async def escalate(envelope: Envelope, error: Exception) -> str:
    """Move the envelope to a terminal FAILED state and surface the failure.

    Returns a short reason label ('budget_exceeded', 'recovery_exhausted', or
    'error') for metrics/logging.
    """
    if isinstance(error, BudgetExceededError):
        event_kind, reason = EventKind.BUDGET_EXCEEDED, "budget_exceeded"
    elif isinstance(error, RecoveryExhaustedError):
        event_kind, reason = EventKind.RECOVERY_EXHAUSTED, "recovery_exhausted"
    else:
        event_kind, reason = EventKind.EXTRACTION_FAILED, "error"

    envelope.advance(
        EnvelopeStatus.FAILED,
        DomainEvent(kind=event_kind, agent="escalation", detail=str(error)),
    )
    await message_bus.publish(envelope.events[-1])
    logger.warning("escalated_to_failed", envelope_id=envelope.id, reason=reason)
    return reason
