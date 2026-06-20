"""Extraction judge — scores extraction results against golden data.

Compares extracted line items, header fields, and totals against
ground-truth labels.  Produces a composite score from 0.0 to 1.0.
"""

from __future__ import annotations

from decimal import Decimal


def score_line_items(extracted: list[dict], expected: list[dict]) -> float:
    """Score line item extraction accuracy.

    Metrics:
      - Item count match (did we get the right number?)
      - Description similarity (fuzzy match)
      - Price accuracy (within tolerance)
    """
    if not expected:
        return 1.0 if not extracted else 0.0

    count_score = 1.0 - abs(len(extracted) - len(expected)) / max(len(expected), 1)
    count_score = max(count_score, 0.0)

    # Match items by description similarity
    matched = 0
    price_errors = []

    for exp_item in expected:
        best_match = None
        best_sim = 0.0

        for ext_item in extracted:
            sim = _description_similarity(
                ext_item.get("description", ""),
                exp_item.get("description", ""),
            )
            if sim > best_sim:
                best_sim = sim
                best_match = ext_item

        if best_match and best_sim > 0.5:
            matched += 1
            # Check price accuracy
            ext_price = Decimal(str(best_match.get("extended_price", 0)))
            exp_price = Decimal(str(exp_item.get("extended_price", 0)))
            if exp_price > 0:
                error = abs(ext_price - exp_price) / exp_price
                price_errors.append(float(error))

    match_rate = matched / len(expected)
    avg_price_error = sum(price_errors) / len(price_errors) if price_errors else 0.0
    price_score = max(0.0, 1.0 - avg_price_error)

    return count_score * 0.3 + match_rate * 0.4 + price_score * 0.3


def score_header(extracted: dict, expected: dict) -> float:
    """Score header extraction.  Simple field-match ratio."""
    if not expected:
        return 1.0

    fields = ["supplier_name", "quote_number", "quote_date", "customer_name"]
    matches = 0
    total = 0

    for field in fields:
        exp_val = expected.get(field)
        if exp_val is not None:
            total += 1
            ext_val = extracted.get(field, "")
            if ext_val and _description_similarity(str(ext_val), str(exp_val)) > 0.8:
                matches += 1

    return matches / total if total > 0 else 1.0


def score_totals(extracted: dict, expected: dict) -> float:
    """Score totals extraction.  Checks key monetary fields within tolerance."""
    if not expected:
        return 1.0

    fields = ["subtotal", "tax_amount", "total"]
    scores = []

    for field in fields:
        exp_val = expected.get(field)
        if exp_val is not None:
            ext_val = extracted.get(field)
            if ext_val is not None:
                exp_d = Decimal(str(exp_val))
                ext_d = Decimal(str(ext_val))
                if exp_d > 0:
                    error = float(abs(ext_d - exp_d) / exp_d)
                    scores.append(max(0.0, 1.0 - error))
                else:
                    scores.append(1.0 if ext_d == 0 else 0.0)
            else:
                scores.append(0.0)

    return sum(scores) / len(scores) if scores else 1.0


def score_extraction(extracted: dict, expected: dict) -> float:
    """Composite score across all extraction components."""
    header_score = score_header(extracted.get("header", {}), expected.get("header", {}))
    items_score = score_line_items(extracted.get("line_items", []), expected.get("line_items", []))
    totals_score = score_totals(extracted.get("totals", {}), expected.get("totals", {}))

    return header_score * 0.2 + items_score * 0.5 + totals_score * 0.3


def _description_similarity(a: str, b: str) -> float:
    """Simple token-overlap similarity."""
    a_tokens = set(a.lower().split())
    b_tokens = set(b.lower().split())
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return len(intersection) / len(union)
