"""Static store — read-only reference data loaded at startup.

Contains supplier catalog entries, known quote formats, and
extraction template hints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent / "data"
_SUPPLIER_CATALOG: dict[str, Any] = {}


def load() -> None:
    """Load static reference data from disk."""
    catalog_path = _DATA_DIR / "supplier_catalog.json"
    if catalog_path.exists():
        global _SUPPLIER_CATALOG
        _SUPPLIER_CATALOG = json.loads(catalog_path.read_text())


def get_supplier_hints(supplier_name: str) -> dict | None:
    """Get extraction hints for a known supplier format."""
    return _SUPPLIER_CATALOG.get(supplier_name.lower())


def known_suppliers() -> list[str]:
    return list(_SUPPLIER_CATALOG.keys())
