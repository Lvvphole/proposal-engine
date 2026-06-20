"""Contractor context retrieval.

Loads contractor-specific preferences that shape proposal generation:
  - Default markup percentages by category
  - Payment terms preferences
  - Branding / header templates
  - Past proposal history for consistency
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

# Placeholder store — production uses database
_CONTRACTOR_PROFILES: dict[str, dict[str, Any]] = {}


def register_contractor(contractor_id: str, profile: dict[str, Any]) -> None:
    """Register or update a contractor's profile."""
    _CONTRACTOR_PROFILES[contractor_id] = profile
    logger.info("contractor_registered", contractor_id=contractor_id)


def get_context(contractor_id: str) -> dict[str, Any]:
    """Retrieve contractor context for proposal generation.

    Returns:
        Dict with keys: markup_rules, payment_terms, branding, history_summary.
        Returns sensible defaults if contractor is unknown.
    """
    profile = _CONTRACTOR_PROFILES.get(contractor_id, {})

    return {
        "contractor_id": contractor_id,
        "markup_rules": profile.get(
            "markup_rules",
            {
                "default_pct": 0.20,
                "materials_pct": 0.15,
                "labor_pct": 0.25,
            },
        ),
        "payment_terms": profile.get("payment_terms", "Due on completion"),
        "branding": profile.get("branding", {}),
        "history_summary": profile.get("history_summary", "No prior proposals on file."),
    }


def list_contractors() -> list[str]:
    return list(_CONTRACTOR_PROFILES.keys())
