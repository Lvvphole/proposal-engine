"""Validation gate — enforces contracts on extraction output.

The gate runs a series of checks against an ExtractionResult.
If any check fails, the result is flagged for review (it is NOT
rejected — humans decide).

Checks:
  1. At least one line item exists
  2. All line items have required fields
  3. Computed subtotal is within tolerance of stated subtotal
  4. No negative prices
  5. Confidence thresholds met
"""

from __future__ import annotations

from decimal import Decimal

import structlog

from contracts.extraction import ExtractionResult

logger = structlog.get_logger()


def validate(result: ExtractionResult) -> bool:
    """Run all validation checks.  Returns True if all pass."""
    checks = [
        _check_line_items_exist(result),
        _check_line_item_fields(result),
        _check_subtotal_consistency(result),
        _check_no_negative_prices(result),
        _check_confidence_threshold(result),
    ]

    passed = all(checks)
    logger.info(
        "validation_gate",
        passed=passed,
        checks_passed=sum(checks),
        checks_total=len(checks),
        pipeline=result.source_pipeline,
    )
    return passed


def _check_line_items_exist(result: ExtractionResult) -> bool:
    if len(result.line_items) == 0:
        logger.warning("validation_no_line_items")
        return False
    return True


def _check_line_item_fields(result: ExtractionResult) -> bool:
    for i, item in enumerate(result.line_items):
        if not item.description.strip():
            logger.warning("validation_empty_description", index=i)
            return False
    return True


def _check_subtotal_consistency(result: ExtractionResult) -> bool:
    if result.totals.subtotal is None:
        return True  # Can't check if no stated subtotal

    computed = result.computed_subtotal
    stated = result.totals.subtotal
    tolerance = max(stated * Decimal("0.02"), Decimal("1.00"))

    if abs(computed - stated) > tolerance:
        logger.warning(
            "validation_subtotal_mismatch",
            computed=str(computed),
            stated=str(stated),
            diff=str(abs(computed - stated)),
        )
        return False
    return True


def _check_no_negative_prices(result: ExtractionResult) -> bool:
    for i, item in enumerate(result.line_items):
        if item.unit_price < 0 or item.extended_price < 0:
            logger.warning("validation_negative_price", index=i)
            return False
    return True


def _check_confidence_threshold(result: ExtractionResult, threshold: float = 0.5) -> bool:
    if result.extraction_confidence < threshold:
        logger.warning(
            "validation_low_confidence",
            confidence=result.extraction_confidence,
            threshold=threshold,
        )
        return False
    return True
