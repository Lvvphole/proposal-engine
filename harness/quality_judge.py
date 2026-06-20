"""Post-extraction quality scoring.

Runs after extraction to produce a quality score that determines
whether the result can proceed to proposal generation or needs
human review.
"""

from __future__ import annotations

from decimal import Decimal

import structlog

from contracts.extraction import ExtractionResult

logger = structlog.get_logger()


def score_extraction(result: ExtractionResult) -> float:
    """Score an extraction result from 0.0 (bad) to 1.0 (perfect).

    Scoring factors:
    - Line item completeness (all required fields present)
    - Totals consistency (computed subtotal matches stated subtotal)
    - Header completeness
    - Overall confidence from the extraction pipeline
    """
    scores: list[float] = []

    # 1. Line item completeness
    complete_items = sum(
        1
        for item in result.line_items
        if item.description and item.quantity > 0 and item.unit_price >= 0
    )
    scores.append(complete_items / max(len(result.line_items), 1))

    # 2. Totals consistency
    if result.totals.subtotal is not None:
        computed = result.computed_subtotal
        diff = abs(computed - result.totals.subtotal)
        tolerance = max(result.totals.subtotal * Decimal("0.01"), Decimal("0.50"))
        scores.append(1.0 if diff <= tolerance else max(0.0, 1.0 - float(diff / tolerance)))
    else:
        scores.append(0.5)  # No stated subtotal to compare against

    # 3. Header completeness
    header = result.header
    header_fields = [header.supplier_name, header.quote_number, header.quote_date]
    scores.append(sum(1 for f in header_fields if f) / len(header_fields))

    # 4. Pipeline confidence
    scores.append(result.extraction_confidence)

    final = sum(scores) / len(scores)
    logger.info("quality_score", score=round(final, 3), components=len(scores))
    return final
