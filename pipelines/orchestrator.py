"""Pipeline orchestrator — the central control loop.

Receives an Envelope, runs classification, dispatches to the correct
extraction pipeline, runs validation, and routes to review.  This is
the top-level entry point for processing a supplier quote.
"""

from __future__ import annotations

import structlog

from contracts.envelope import Envelope, EnvelopeStatus
from contracts.events import DomainEvent, EventKind
from contracts.errors import BudgetExceededError, RecoveryExhaustedError
from core import message_bus
from harness.budget import check_budget
from harness.escalation import escalate
from harness.instrumentation import increment, timer
from pipelines.pipeline_a.run import run as run_pipeline_a
from pipelines.pipeline_b.run import run as run_pipeline_b
from pipelines.pipeline_c.run import run as run_pipeline_c
from pipelines.validation_gate import validate

logger = structlog.get_logger()

_PIPELINE_MAP = {
    "a": run_pipeline_a,
    "b": run_pipeline_b,
    "c": run_pipeline_c,
}


async def process_envelope(envelope: Envelope) -> Envelope:
    """Run the full extraction pipeline on an envelope.

    Flow:
        1. Budget pre-check
        2. Classification (determines pipeline)
        3. Extraction (pipeline A, B, or C)
        4. Validation gate
        5. Route to review surface

    Returns the envelope with updated status and populated extraction data.
    """
    with timer("orchestrator.total"):
        try:
            # 1. Budget pre-check
            check_budget(envelope)

            # 2. Classification
            envelope.advance(
                EnvelopeStatus.CLASSIFYING,
                DomainEvent(kind=EventKind.RECEIVED, agent="orchestrator"),
            )
            # Classification is handled within each pipeline's run()
            # For now, we route based on pre-set classification
            if envelope.classification is None:
                # Default to pipeline C if no classification
                pipeline_id = "c"
            else:
                pipeline_id = envelope.classification.pipeline

            # 3. Extraction
            envelope.advance(
                EnvelopeStatus.EXTRACTING,
                DomainEvent(
                    kind=EventKind.EXTRACTION_STARTED,
                    agent="orchestrator",
                    detail=f"pipeline_{pipeline_id}",
                ),
            )

            pipeline_fn = _PIPELINE_MAP[pipeline_id]
            extraction_result = await pipeline_fn(envelope)
            envelope.extraction = extraction_result

            envelope.advance(
                EnvelopeStatus.VALIDATING,
                DomainEvent(
                    kind=EventKind.EXTRACTION_COMPLETED,
                    agent=f"pipeline_{pipeline_id}",
                ),
            )
            increment("extractions.completed")

            # 4. Validation gate
            validation_passed = validate(extraction_result)

            if validation_passed:
                envelope.advance(
                    EnvelopeStatus.REVIEW_PENDING,
                    DomainEvent(
                        kind=EventKind.VALIDATION_PASSED,
                        agent="validation_gate",
                    ),
                )
                increment("validations.passed")
            else:
                envelope.advance(
                    EnvelopeStatus.REVIEW_PENDING,
                    DomainEvent(
                        kind=EventKind.VALIDATION_FAILED,
                        agent="validation_gate",
                        detail="Extraction flagged for manual review",
                    ),
                )
                increment("validations.failed")

            # 5. Route to review
            await message_bus.publish(
                DomainEvent(
                    kind=EventKind.REVIEW_REQUESTED,
                    agent="orchestrator",
                    metadata={"envelope_id": envelope.id},
                )
            )

        except BudgetExceededError as e:
            await escalate(envelope, e)
            increment("errors.budget_exceeded")

        except RecoveryExhaustedError as e:
            await escalate(envelope, e)
            increment("errors.recovery_exhausted")

        except Exception as e:
            logger.error("orchestrator_error", error=str(e), envelope_id=envelope.id)
            action = await escalate(envelope, e)
            increment(f"errors.escalated_to_{action}")

    return envelope
