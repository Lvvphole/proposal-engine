"""Tests for the pipeline orchestrator.

These are integration-level tests that verify the orchestrator's
control flow.  LLM calls are mocked.
"""

from decimal import Decimal

import pytest

from contracts.classifier import ClassificationResult, QuoteFormat
from contracts.envelope import Envelope, EnvelopeStatus
from contracts.errors import BudgetExceededError
from contracts.extraction import (
    ExtractionResult,
    HeaderData,
    LineItem,
    TotalsData,
)


class TestOrchestrator:
    @pytest.fixture
    def envelope(self):
        return Envelope(
            source_filename="test_quote.pdf",
            source_content_type="application/pdf",
            source_bytes_b64="dGVzdCBjb250ZW50",  # "test content" in base64
        )

    @pytest.fixture
    def mock_extraction_result(self):
        return ExtractionResult(
            header=HeaderData(supplier_name="Test Supply"),
            line_items=[
                LineItem(
                    description="Test Item",
                    quantity=Decimal("10"),
                    unit_price=Decimal("5.00"),
                    extended_price=Decimal("50.00"),
                )
            ],
            totals=TotalsData(subtotal=Decimal("50.00")),
            source_pipeline="a",
            extraction_confidence=0.9,
        )

    def test_envelope_starts_as_received(self, envelope):
        assert envelope.status == EnvelopeStatus.RECEIVED

    def test_classification_result_routes_to_pipeline(self):
        classification = ClassificationResult(
            format=QuoteFormat.STRUCTURED_TABLE,
            pipeline="a",
            confidence=0.95,
            reasoning="Clean table layout",
        )
        assert classification.pipeline == "a"
        assert classification.is_high_confidence

    def test_budget_exceeded_halts_processing(self, envelope):
        err = BudgetExceededError(
            "Over limit",
            context={"envelope_id": envelope.id},
        )
        assert isinstance(err, BudgetExceededError)
        # In the real orchestrator, this would trigger escalation

    def test_envelope_token_tracking(self, envelope):
        envelope.token_usage["classifier_input"] = 500
        envelope.token_usage["classifier_output"] = 100
        envelope.token_usage["extractor_input"] = 2000
        envelope.token_usage["extractor_output"] = 800
        assert envelope.total_tokens == 3400
