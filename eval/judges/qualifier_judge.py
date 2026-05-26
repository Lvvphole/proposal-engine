"""Qualifier judge — determines if an extraction meets the quality
bar for automatic proposal generation vs. requiring human review.

This is a binary classifier: PASS or REVIEW_NEEDED.
"""

from __future__ import annotations


def qualify(extraction: dict, *, threshold: float = 0.75) -> dict:
    """Assess whether an extraction passes the quality bar.

    Returns:
        Dict with keys: qualified (bool), score (float), reasons (list[str]).
    """
    reasons = []
    score_components = []

    # Check line item count
    items = extraction.get("line_items", [])
    if not items:
        reasons.append("No line items extracted")
        score_components.append(0.0)
    else:
        score_components.append(1.0)

    # Check for low-confidence items
    low_conf_items = [i for i in items if i.get("confidence", 1.0) < 0.5]
    if low_conf_items:
        reasons.append(f"{len(low_conf_items)} items below 0.5 confidence")
        score_components.append(1.0 - len(low_conf_items) / len(items))
    else:
        score_components.append(1.0)

    # Check header completeness
    header = extraction.get("header", {})
    if not header.get("supplier_name"):
        reasons.append("Missing supplier name")
        score_components.append(0.0)
    else:
        score_components.append(1.0)

    # Check totals presence
    totals = extraction.get("totals", {})
    if totals.get("total") is None and totals.get("subtotal") is None:
        reasons.append("No total or subtotal found")
        score_components.append(0.5)
    else:
        score_components.append(1.0)

    score = sum(score_components) / len(score_components) if score_components else 0.0

    return {
        "qualified": score >= threshold and not reasons,
        "score": round(score, 3),
        "reasons": reasons,
    }
