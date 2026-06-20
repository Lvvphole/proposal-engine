"""Tests for the Proposal Builder (pure pricing) + orchestrator wiring."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from contracts.contractor import ContractorProfile
from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData
from pipelines.proposal_builder import build_proposal


def _extraction(tax_rate: Decimal | None = Decimal("0.10")) -> ExtractionResult:
    return ExtractionResult(
        header=HeaderData(supplier_name="ABC Supply", delivery_terms="FOB Origin"),
        line_items=[
            LineItem(
                description="Plywood",
                quantity=Decimal("2"),
                unit_price=Decimal("10.00"),
                extended_price=Decimal("20.00"),
            ),
            LineItem(
                description="Nails",
                quantity=Decimal("1"),
                unit_price=Decimal("5.00"),
                extended_price=Decimal("5.00"),
            ),
        ],
        totals=TotalsData(subtotal=Decimal("25.00"), tax_rate=tax_rate),
        source_pipeline="a",
    )


def test_applies_default_markup_and_tax():
    contractor = ContractorProfile(
        id="c1", name="Acme", default_markup_pct=0.20, payment_terms="Net 30"
    )
    proposal = build_proposal(_extraction(), contractor)

    # Per-line markup at 20%.
    assert proposal.line_items[0].unit_price == Decimal("12.00")
    assert proposal.line_items[0].extended_price == Decimal("24.00")
    assert proposal.line_items[1].extended_price == Decimal("6.00")

    assert proposal.cost_subtotal == Decimal("25.00")
    assert proposal.subtotal == Decimal("30.00")
    assert proposal.markup_amount == Decimal("5.00")
    assert proposal.tax_rate == Decimal("0.10")
    assert proposal.tax_amount == Decimal("3.00")  # 10% of 30.00
    assert proposal.total == Decimal("33.00")

    assert proposal.payment_terms == "Net 30"
    assert proposal.delivery_terms == "FOB Origin"
    assert proposal.contractor_id == "c1"


def test_rounds_to_cents_half_up():
    extraction = ExtractionResult(
        header=HeaderData(supplier_name="X"),
        line_items=[
            LineItem(
                description="Widget",
                quantity=Decimal("1"),
                unit_price=Decimal("9.99"),
                extended_price=Decimal("9.99"),
            )
        ],
        totals=TotalsData(),
        source_pipeline="c",
    )
    contractor = ContractorProfile(id="c", name="N", default_markup_pct=0.175)
    proposal = build_proposal(extraction, contractor)
    # 9.99 * 1.175 = 11.73825 → 11.74
    assert proposal.line_items[0].extended_price == Decimal("11.74")


def test_no_tax_rate_means_no_tax():
    contractor = ContractorProfile(id="c", name="N", default_markup_pct=0.10)
    proposal = build_proposal(_extraction(tax_rate=None), contractor)
    assert proposal.tax_amount == Decimal("0.00")
    assert proposal.total == proposal.subtotal


def test_default_contractor_id_is_normalised_to_none():
    contractor = ContractorProfile(id="default", name="(default)")
    proposal = build_proposal(_extraction(), contractor)
    assert proposal.contractor_id is None


@pytest.mark.asyncio
async def test_orchestrator_attaches_proposal():
    from contracts.classifier import ClassificationResult, QuoteFormat
    from contracts.envelope import Envelope, EnvelopeStatus
    from pipelines import orchestrator

    extraction = _extraction()

    async def fake_pipeline(_env: Envelope) -> ExtractionResult:
        return extraction

    envelope = Envelope(
        source_content_type="text/plain",
        source_bytes_b64="QQ==",
        classification=ClassificationResult(
            format=QuoteFormat.STRUCTURED_TABLE,
            pipeline="a",
            confidence=0.95,
            reasoning="clean table",
        ),
    )

    with (
        patch.dict(orchestrator._PIPELINE_MAP, {"a": fake_pipeline}),
        patch.object(orchestrator, "_checkpoint", AsyncMock()),
        patch.object(
            orchestrator,
            "_load_contractor",
            AsyncMock(
                return_value=ContractorProfile(id="c1", name="Acme", default_markup_pct=0.20)
            ),
        ),
        patch.object(orchestrator.message_bus, "publish", AsyncMock()),
    ):
        result = await orchestrator.process_envelope(envelope)

    assert result.status == EnvelopeStatus.REVIEW_PENDING
    assert result.proposal is not None
    assert result.proposal.contractor_id == "c1"
    assert result.proposal.total == Decimal("33.00")
    assert result.contractor_markup_pct == 0.20
