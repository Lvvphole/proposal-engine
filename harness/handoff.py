"""Agent-to-agent handoff protocol.

Enforces that data crossing agent boundaries satisfies the typed
contracts.  Logs the handoff for observability.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ValidationError as PydanticValidationError

from contracts.errors import ContractViolation

logger = structlog.get_logger()


def validate_handoff(
    data: dict | BaseModel,
    contract: type[BaseModel],
    *,
    source_agent: str,
    target_agent: str,
) -> BaseModel:
    """Validate data against a contract at an agent boundary.

    Args:
        data: Raw data dict or already-parsed model.
        contract: The Pydantic model class to validate against.
        source_agent: Name of the producing agent.
        target_agent: Name of the consuming agent.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ContractViolation: If data doesn't conform to the contract.
    """
    try:
        if isinstance(data, BaseModel):
            validated = contract.model_validate(data.model_dump())
        else:
            validated = contract.model_validate(data)
    except PydanticValidationError as e:
        raise ContractViolation(
            f"Handoff {source_agent} → {target_agent} failed: {e.error_count()} errors",
            context={
                "source": source_agent,
                "target": target_agent,
                "errors": e.errors(),
            },
        ) from e

    logger.info(
        "handoff_validated",
        source=source_agent,
        target=target_agent,
        contract=contract.__name__,
    )
    return validated
