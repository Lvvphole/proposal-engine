import pytest

"""Tests for the validation gate."""

from decimal import Decimal

from contracts.extraction import (
    ExtractionResult,
    HeaderData,
    LineItem,
    TotalsData,
)
from pipelines.validation_gate import validate


def _make_result(**overrides) -> ExtractionResult:
    """Helper to build a valid ExtractionResult with optional overrides."""
    defaults = {
        "header": HeaderData(
            supplier_name="Test Supply", quote_number="Q-001", quote_date="2024-01-01"
        ),
        "line_items": [
            LineItem(
                description="Test Item",
                quantity=Decimal("10"),
                unit_price=Decimal("5.00"),
                extended_price=Decimal("50.00"),
                confidence=0.95,
            )
        ],
        "totals": TotalsData(subtotal=Decimal("50.00"), total=Decimal("50.00")),
        "source_pipeline": "a",
        "extraction_confidence": 0.9,
    }
    defaults.update(overrides)
    return ExtractionResult(**defaults)


class TestValidationGate:
    def test_valid_extraction_passes(self):
        result = _make_result()
        assert validate(result) is True

    def test_subtotal_mismatch_fails(self):
        result = _make_result(
            totals=TotalsData(subtotal=Decimal("999.00"), total=Decimal("999.00"))
        )
        assert validate(result) is False

    def test_low_confidence_fails(self):
        result = _make_result(extraction_confidence=0.3)
        assert validate(result) is False

    def test_negative_price_fails(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            _make_result(
                line_items=[
                    LineItem(
                        description="Bad Item",
                        quantity=Decimal("1"),
                        unit_price=Decimal("10.00"),
                        extended_price=Decimal("-10.00"),
                    )
                ]
            )

    def test_no_stated_subtotal_still_passes(self):
        result = _make_result(
            totals=TotalsData()  # No subtotal to check against
        )
        assert validate(result) is True

    def test_within_tolerance_passes(self):
        # Subtotal is $50.00, stated is $50.50 — within 2% tolerance
        result = _make_result(totals=TotalsData(subtotal=Decimal("50.50"), total=Decimal("50.50")))
        assert validate(result) is True
