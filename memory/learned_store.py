"""Learned store — patterns captured from human corrections.

When a reviewer edits an extraction before approving, the diff
is stored here so future extractions from the same supplier
can incorporate the correction.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# In-memory for now; production uses the database
_corrections: dict[str, list[dict]] = {}


def record_correction(supplier_name: str, correction: dict) -> None:
    """Store a human correction for a supplier."""
    key = supplier_name.lower()
    _corrections.setdefault(key, []).append(correction)
    logger.info("correction_recorded", supplier=key, total=len(_corrections[key]))


def get_corrections(supplier_name: str, limit: int = 5) -> list[dict]:
    """Retrieve recent corrections for a supplier."""
    return _corrections.get(supplier_name.lower(), [])[-limit:]
