"""Escalation routing for pipeline failures.

When an agent fails and retries are exhausted, the escalation module
decides the next step:
  1. Route to recovery agent (automated fix attempt)
  2. Route to Pipeline C fallback (broad extraction)
  3. Escalate to human review with failure context
"""

from __future__ import annotations

import structlog

from contracts.envelope import Envelope, EnvelopeStatus
from contracts.events import DomainEvent, EventKind
from contracts.errors import BudgetExceededError, RecoveryExhaustedError
from core import message_bus

logger = structlog.get_logger()


async def escalate(envelope: Envelope, error: Exception) -> str:
    """Determine escalation path and update envelope status.

    Returns:
        The escalation action taken: 'recovery', 'fallback', or 'human_review'.
    """
    if isinstance(error, BudgetExceededError):
        # Budget exceeded → always human review, no further LLM calls
        envelope.advance(
            EnvelopeStatus.REVIEW_PENDING,
            DomainEvent(
                kind=EventKind.BUDGET_EXCEEDED,
                agent="escalation",
                detail=str(error),
            ),
        )
        await message_bus.publish(envelope.events[-1])
        logger.warning("escalation_budget_exceeded", envelope_id=envelope.id)
        return "human_review"

    if isinstance(error, RecoveryExhaustedError):
        # All retries spent → human review
        envelope.advance(
            EnvelopeStatus.REVIEW_PENDING,
            DomainEvent(
                kind=EventKind.RECOVERY_EXHAUSTED,
                agent="escalation",
                detail=str(error),
            ),
        )
        await message_bus.publish(envelope.events[-1])
        logger.warning("escalation_recovery_exhausted", envelope_id=envelope.id)
        return "human_review"

    # Default: attempt recovery agent
    envelope.advance(
        EnvelopeStatus.EXTRACTING,
        DomainEvent(
            kind=EventKind.RECOVERY_ATTEMPTED,
            agent="escalation",
            detail=f"Routing to recovery agent: {error}",
        ),
    )
    await message_bus.publish(envelope.events[-1])
    logger.info("escalation_to_recovery", envelope_id=envelope.id)
    return "recovery"
