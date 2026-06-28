"""Tests for extraction recovery + terminal failure routing."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from contracts.classifier import ClassificationResult, QuoteFormat
from contracts.contractor import ContractorProfile
from contracts.envelope import Envelope, EnvelopeStatus
from contracts.errors import BudgetExceededError, ExtractionError, RecoveryExhaustedError
from contracts.events import EventKind
from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData


def _result(pipeline: str = "c") -> ExtractionResult:
    return ExtractionResult(
        header=HeaderData(supplier_name="ABC Supply"),
        line_items=[
            LineItem(
                description="Plywood",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                extended_price=Decimal("10.00"),
            )
        ],
        totals=TotalsData(subtotal=Decimal("10.00")),
        source_pipeline=pipeline,
    )


async def _fail(_envelope: Envelope) -> ExtractionResult:
    raise ExtractionError("no line items extracted", context={})


async def _ok(_envelope: Envelope) -> ExtractionResult:
    return _result()


def _classified(pipeline: str) -> Envelope:
    return Envelope(
        classification=ClassificationResult(
            format=QuoteFormat.STRUCTURED_TABLE,
            pipeline=pipeline,
            confidence=0.95,
            reasoning="clean table",
        )
    )


# ── _extract_with_recovery ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recovers_via_pipeline_c():
    from pipelines import orchestrator

    env = Envelope()
    with patch.dict(orchestrator._PIPELINE_MAP, {"a": _fail, "c": _ok}):
        result = await orchestrator._extract_with_recovery(env, "a")

    assert result.source_pipeline == "c"
    kinds = [e.kind for e in env.events]
    assert EventKind.RECOVERY_ATTEMPTED in kinds
    assert EventKind.RECOVERY_SUCCEEDED in kinds


@pytest.mark.asyncio
async def test_exhausted_raises_recovery_exhausted():
    from pipelines import orchestrator

    env = Envelope()
    with (
        patch.dict(orchestrator._PIPELINE_MAP, {"a": _fail, "c": _fail}),
        pytest.raises(RecoveryExhaustedError),
    ):
        await orchestrator._extract_with_recovery(env, "a")


@pytest.mark.asyncio
async def test_pipeline_c_makes_a_single_attempt():
    from pipelines import orchestrator

    calls: list[str] = []

    async def fail_c(_env: Envelope) -> ExtractionResult:
        calls.append("c")
        raise ExtractionError("x", context={})

    env = Envelope()
    with (
        patch.dict(orchestrator._PIPELINE_MAP, {"c": fail_c}),
        pytest.raises(RecoveryExhaustedError),
    ):
        await orchestrator._extract_with_recovery(env, "c")
    assert calls == ["c"]  # no fallback when already on C


@pytest.mark.asyncio
async def test_budget_error_is_not_recovered():
    from pipelines import orchestrator

    async def budget(_env: Envelope) -> ExtractionResult:
        raise BudgetExceededError("over limit", context={})

    env = Envelope()
    with (
        patch.dict(orchestrator._PIPELINE_MAP, {"a": budget, "c": _ok}),
        pytest.raises(BudgetExceededError),
    ):
        await orchestrator._extract_with_recovery(env, "a")


# ── escalate → terminal FAILED ───────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,reason",
    [
        (ExtractionError("e", context={}), "error"),
        (RecoveryExhaustedError("e", context={}), "recovery_exhausted"),
        (BudgetExceededError("e", context={}), "budget_exceeded"),
    ],
)
async def test_escalate_sets_failed(error, reason):
    from core import message_bus
    from harness.escalation import escalate

    env = Envelope()
    with patch.object(message_bus, "publish", AsyncMock()):
        result = await escalate(env, error)
    assert env.status == EnvelopeStatus.FAILED
    assert result == reason


# ── Orchestrator integration ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_recovers_and_reaches_review():
    from pipelines import orchestrator

    env = _classified("a")
    with (
        patch.dict(orchestrator._PIPELINE_MAP, {"a": _fail, "c": _ok}),
        patch.object(orchestrator, "_checkpoint", AsyncMock()),
        patch.object(
            orchestrator,
            "_load_contractor",
            AsyncMock(return_value=ContractorProfile(id="c1", name="N")),
        ),
        patch.object(orchestrator.message_bus, "publish", AsyncMock()),
    ):
        result = await orchestrator.process_envelope(env)

    assert result.status == EnvelopeStatus.REVIEW_PENDING
    assert result.proposal is not None


@pytest.mark.asyncio
async def test_orchestrator_failure_is_terminal_not_stranded():
    from pipelines import orchestrator

    env = _classified("a")
    with (
        patch.dict(orchestrator._PIPELINE_MAP, {"a": _fail, "c": _fail}),
        patch.object(orchestrator, "_checkpoint", AsyncMock()),
        patch.object(orchestrator.message_bus, "publish", AsyncMock()),
    ):
        result = await orchestrator.process_envelope(env)

    # The bug being fixed: a failed extraction must reach a terminal state,
    # never strand in 'extracting'.
    assert result.status == EnvelopeStatus.FAILED
    assert result.status != EnvelopeStatus.EXTRACTING
