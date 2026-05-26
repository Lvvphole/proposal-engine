"""Tests for the contracts layer — validates that all typed contracts
enforce their invariants correctly.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from contracts.extraction import (
    ExtractionResult,
    HeaderData,
    LineItem,
    TotalsData,
    UnitOfMeasure,
)
from contracts.classifier import ClassificationResult, QuoteFormat
from contracts.envelope import Envelope, EnvelopeStatus
from contracts.events import DomainEvent, EventKind
from contracts.errors import ContractViolation, BudgetExceededError


class TestLineItem:
    def test_valid_line_item(self):
        item = LineItem(
            sku="PLY-001",
            description="CDX Plywood 1/2 4x8",
            quantity=Decimal("100"),
            unit=UnitOfMeasure.EACH,
            unit_price=Decimal("28.75"),
            extended_price=Decimal("2875.00"),
        )
        assert item.description == "CDX Plywood 1/2 4x8"
        assert item.confidence == 1.0

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            LineItem(
                description="Test",
                quantity=Decimal("0"),
                unit_price=Decimal("10"),
                extended_price=Decimal("0"),
            )

    def test_negative_unit_price_rejected(self):
        with pytest.raises(ValidationError):
            LineItem(
                description="Test",
                quantity=Decimal("1"),
                unit_price=Decimal("-5"),
                extended_price=Decimal("-5"),
            )

    def test_empty_description_rejected(self):
        with pytest.raises(ValidationError):
            LineItem(
                description="",
                quantity=Decimal("1"),
                unit_price=Decimal("10"),
                extended_price=Decimal("10"),
            )


class TestTotalsData:
    def test_valid_totals(self):
        totals = TotalsData(
            subtotal=Decimal("5000.00"),
            tax_amount=Decimal("350.00"),
            tax_rate=Decimal("0.07"),
            total=Decimal("5350.00"),
        )
        assert totals.tax_rate == Decimal("0.07")

    def test_unreasonable_tax_rate_rejected(self):
        with pytest.raises(ValidationError):
            TotalsData(tax_rate=Decimal("0.50"))

    def test_null_fields_allowed(self):
        totals = TotalsData()
        assert totals.subtotal is None
        assert totals.total is None


class TestExtractionResult:
    def test_computed_subtotal(self):
        result = ExtractionResult(
            header=HeaderData(supplier_name="Test Supply"),
            line_items=[
                LineItem(
                    description="Item A",
                    quantity=Decimal("10"),
                    unit_price=Decimal("5.00"),
                    extended_price=Decimal("50.00"),
                ),
                LineItem(
                    description="Item B",
                    quantity=Decimal("3"),
                    unit_price=Decimal("20.00"),
                    extended_price=Decimal("60.00"),
                ),
            ],
            totals=TotalsData(subtotal=Decimal("110.00")),
            source_pipeline="a",
        )
        assert result.computed_subtotal == Decimal("110.00")
        assert result.line_item_count == 2

    def test_at_least_one_line_item_required(self):
        with pytest.raises(ValidationError):
            ExtractionResult(
                header=HeaderData(supplier_name="Test"),
                line_items=[],
                totals=TotalsData(),
                source_pipeline="a",
            )


class TestClassificationResult:
    def test_high_confidence(self):
        result = ClassificationResult(
            format=QuoteFormat.STRUCTURED_TABLE,
            pipeline="a",
            confidence=0.95,
            reasoning="Clean tabular layout with headers",
        )
        assert result.is_high_confidence
        assert not result.needs_fallback

    def test_low_confidence_needs_fallback(self):
        result = ClassificationResult(
            format=QuoteFormat.UNSTRUCTURED_FREETEXT,
            pipeline="c",
            confidence=0.3,
            reasoning="Unclear format",
        )
        assert result.needs_fallback

    def test_invalid_pipeline_rejected(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                format=QuoteFormat.STRUCTURED_TABLE,
                pipeline="x",
                confidence=0.9,
                reasoning="Test",
            )


class TestEnvelope:
    def test_default_status(self):
        env = Envelope()
        assert env.status == EnvelopeStatus.RECEIVED
        assert env.total_tokens == 0

    def test_advance(self):
        env = Envelope()
        event = DomainEvent(kind=EventKind.CLASSIFIED, agent="classifier")
        env.advance(EnvelopeStatus.CLASSIFYING, event)
        assert env.status == EnvelopeStatus.CLASSIFYING
        assert len(env.events) == 1

    def test_token_accumulation(self):
        env = Envelope()
        env.token_usage["classifier_input"] = 500
        env.token_usage["classifier_output"] = 100
        assert env.total_tokens == 600


class TestErrors:
    def test_contract_violation(self):
        err = ContractViolation("bad data", context={"field": "quantity"})
        assert "bad data" in str(err)
        assert err.context["field"] == "quantity"

    def test_budget_exceeded(self):
        err = BudgetExceededError("over limit", context={"cost": "3.50"})
        assert err.context["cost"] == "3.50"
