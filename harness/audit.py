"""Immutable audit log.

Appends domain events to a structured log file and (optionally) a
database table.  Events are never mutated or deleted.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from contracts.events import DomainEvent

logger = structlog.get_logger()

_AUDIT_LOG_PATH = Path("audit.jsonl")


async def record(event: DomainEvent, envelope_id: str) -> None:
    """Append an event to the audit log."""
    entry = {
        "envelope_id": envelope_id,
        "event": event.model_dump(mode="json"),
    }
    with _AUDIT_LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    logger.info(
        "audit_recorded",
        envelope_id=envelope_id,
        event_kind=event.kind,
    )
