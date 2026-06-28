"""Tests for the eval runner — guards that the suites actually score
(rather than the old always-pass stub) and fail on bad data."""

from __future__ import annotations

import pytest

from eval.run_evals import (
    DEFAULT_SUITES,
    _score_classifier,
    _score_line_items,
    _score_pricing,
    _score_recovery,
    run_suite,
)


@pytest.mark.parametrize("suite", DEFAULT_SUITES)
def test_suite_scores_real_cases_at_baseline(suite):
    result = run_suite(suite)
    assert result["total"] > 0
    assert result["accuracy"] == 1.0


def test_classifier_scorer_fails_on_wrong_route():
    model_response = (
        '{"format": "unstructured", "pipeline": "c", "confidence": 0.9, "reasoning": "x"}'
    )
    ok, _ = _score_classifier(
        {
            "model_response": model_response,
            "expected": {"format": "structured_table", "pipeline": "a"},
        }
    )
    assert not ok


def test_line_items_scorer_fails_on_garbage_output():
    ok, score = _score_line_items(
        {
            "model_response": "sorry, no JSON here",
            "expected": {
                "line_items": [
                    {
                        "description": "Plywood",
                        "quantity": 2,
                        "unit": "each",
                        "unit_price": 10,
                        "extended_price": 20,
                    }
                ]
            },
        }
    )
    assert not ok
    assert score < 0.85


def test_pricing_scorer_fails_on_wrong_total():
    ok, _ = _score_pricing(
        {
            "extraction": {
                "header": {"supplier_name": "X"},
                "line_items": [
                    {
                        "description": "A",
                        "quantity": "1",
                        "unit": "each",
                        "unit_price": "10.00",
                        "extended_price": "10.00",
                    }
                ],
                "totals": {"subtotal": "10.00"},
                "source_pipeline": "a",
            },
            "contractor": {"id": "c", "name": "N", "default_markup_pct": 0.2},
            "expected": {
                "subtotal": "999.00",
                "markup_amount": "0",
                "tax_amount": "0",
                "total": "999.00",
            },
        }
    )
    assert not ok


def test_recovery_scorer_detects_and_ignores():
    detected, _ = _score_recovery(
        {
            "error": "subtotal_mismatch",
            "failed_extraction": {"totals": {"subtotal": 5102.5}},
            "computed_subtotal": 4732.5,
        }
    )
    assert detected

    not_detected, _ = _score_recovery(
        {
            "error": "line_item_count_mismatch",
            "failed_extraction": {"line_items": [1, 2, 3, 4, 5]},
            "expected_count": 5,
        }
    )
    assert not not_detected  # counts match → nothing to recover
