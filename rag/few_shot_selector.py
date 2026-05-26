"""Few-shot example selector.

Selects the most relevant extraction examples to include in agent
prompts.  Uses embedding similarity + supplier matching to pick
examples that maximize extraction accuracy.
"""

from __future__ import annotations

from typing import Any

import structlog

from rag import embeddings

logger = structlog.get_logger()

# Pre-loaded examples: list of {document_snippet, extraction_result, supplier, pipeline}
_examples: list[dict[str, Any]] = []


def add_example(
    document_snippet: str,
    extraction_result: dict,
    supplier: str = "",
    pipeline: str = "",
) -> None:
    """Add a verified extraction example to the few-shot pool."""
    _examples.append({
        "document_snippet": document_snippet[:1000],
        "extraction_result": extraction_result,
        "supplier": supplier.lower(),
        "pipeline": pipeline,
    })
    logger.info("few_shot_example_added", total=len(_examples), supplier=supplier)


async def select(
    query_text: str,
    *,
    supplier_hint: str = "",
    pipeline: str = "",
    k: int = 2,
) -> list[dict]:
    """Select the best few-shot examples for a given extraction task.

    Priority:
    1. Same supplier + same pipeline (exact match)
    2. Same supplier, any pipeline
    3. Embedding similarity across all examples
    """
    # Tier 1: exact supplier + pipeline match
    exact = [
        ex for ex in _examples
        if ex["supplier"] == supplier_hint.lower() and ex["pipeline"] == pipeline
    ]
    if len(exact) >= k:
        return exact[:k]

    # Tier 2: same supplier
    supplier_match = [ex for ex in _examples if ex["supplier"] == supplier_hint.lower()]
    if len(supplier_match) >= k:
        return supplier_match[:k]

    # Tier 3: embedding similarity fallback
    if _examples:
        results = await embeddings.search(query_text, k=k)
        return results[:k]

    return []
