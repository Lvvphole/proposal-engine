"""Supplier catalog — known supplier formats and extraction hints.

Maintains a registry of suppliers we've seen before, including:
  - Known quote formats (which pipeline works best)
  - Field mapping hints (where on the page each field tends to appear)
  - Historical extraction accuracy
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

# supplier_name (lowercase) → catalog entry
_catalog: dict[str, dict[str, Any]] = {}


def register_supplier(
    name: str,
    *,
    preferred_pipeline: str = "c",
    field_hints: dict | None = None,
    avg_accuracy: float = 0.0,
    notes: str = "",
) -> None:
    """Register or update a supplier in the catalog."""
    _catalog[name.lower()] = {
        "name": name,
        "preferred_pipeline": preferred_pipeline,
        "field_hints": field_hints or {},
        "avg_accuracy": avg_accuracy,
        "extraction_count": _catalog.get(name.lower(), {}).get("extraction_count", 0),
        "notes": notes,
    }
    logger.info("supplier_registered", supplier=name, pipeline=preferred_pipeline)


def get_supplier(name: str) -> dict[str, Any] | None:
    return _catalog.get(name.lower())


def get_preferred_pipeline(name: str) -> str | None:
    entry = _catalog.get(name.lower())
    return entry["preferred_pipeline"] if entry else None


def record_extraction(name: str, accuracy: float) -> None:
    """Update running accuracy stats after an extraction."""
    entry = _catalog.get(name.lower())
    if entry:
        count = entry["extraction_count"] + 1
        entry["avg_accuracy"] = (
            (entry["avg_accuracy"] * entry["extraction_count"] + accuracy) / count
        )
        entry["extraction_count"] = count


def list_suppliers() -> list[str]:
    return [v["name"] for v in _catalog.values()]
