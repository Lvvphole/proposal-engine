"""Retrieval store — embedding-based few-shot example selection.

Stores extraction examples as embeddings.  When processing a new
document, retrieves the most similar past examples to use as
few-shot prompts.

Placeholder implementation — production uses a vector DB.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

_examples: list[dict[str, Any]] = []


def add_example(document_text: str, extraction: dict, metadata: dict | None = None) -> None:
    """Add a successful extraction as a few-shot example."""
    _examples.append(
        {
            "text": document_text[:1000],
            "extraction": extraction,
            "metadata": metadata or {},
        }
    )
    logger.info("example_added", total=len(_examples))


def retrieve_similar(query_text: str, k: int = 3) -> list[dict]:
    """Retrieve k most similar examples.  Placeholder: returns most recent."""
    return _examples[-k:]


def count() -> int:
    return len(_examples)
