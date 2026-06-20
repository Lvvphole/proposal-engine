"""Tests for the Review Surface API: extraction fetch + review submission."""

from __future__ import annotations

import os
from decimal import Decimal

import pytest


@pytest.fixture
async def session(tmp_path):
    db_file = tmp_path / "review_api.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    from core.config import get_config

    get_config.cache_clear()
    from core.db import _get_session_factory, init_db, reset_engine

    reset_engine()
    await init_db()
    async with _get_session_factory()() as s:
        yield s
    reset_engine()
    get_config.cache_clear()
    os.environ["DATABASE_URL"] = "sqlite:///./test_proposals.db"


def _envelope_with_extraction():
    from contracts.envelope import Envelope, EnvelopeStatus
    from contracts.events import DomainEvent, EventKind
    from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData

    env = Envelope(source_filename="quote.pdf")
    env.extraction = ExtractionResult(
        header=HeaderData(supplier_name="ABC Supply", quote_number="Q-1"),
        line_items=[
            LineItem(
                description="Plywood",
                quantity=Decimal("2"),
                unit_price=Decimal("10.00"),
                extended_price=Decimal("20.00"),
                confidence=0.95,
            )
        ],
        totals=TotalsData(subtotal=Decimal("20.00"), total=Decimal("20.00")),
        source_pipeline="a",
        extraction_confidence=0.9,
    )
    env.advance(
        EnvelopeStatus.REVIEW_PENDING,
        DomainEvent(kind=EventKind.VALIDATION_PASSED, agent="test"),
    )
    return env


@pytest.mark.asyncio
async def test_get_extraction_returns_data(session):
    from app.api.routes import get_quote_extraction
    from harness.models import save_envelope

    env = _envelope_with_extraction()
    await save_envelope(env, session)

    result = await get_quote_extraction(env.id, session=session)
    assert result["header"]["supplier_name"] == "ABC Supply"
    assert len(result["line_items"]) == 1
    assert result["line_items"][0]["description"] == "Plywood"
    assert result["totals"]["total"] == "20.00"
    assert result["quality_score"] == 0.9


@pytest.mark.asyncio
async def test_get_extraction_404_unknown(session):
    from fastapi import HTTPException

    from app.api.routes import get_quote_extraction

    with pytest.raises(HTTPException) as exc:
        await get_quote_extraction("nope", session=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_extraction_409_when_not_extracted(session):
    from fastapi import HTTPException

    from app.api.routes import get_quote_extraction
    from contracts.envelope import Envelope
    from harness.models import save_envelope

    env = Envelope(source_filename="raw.pdf")
    await save_envelope(env, session)

    with pytest.raises(HTTPException) as exc:
        await get_quote_extraction(env.id, session=session)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_contractor_ignores_explicit_null(session):
    from app.api.contractors import ContractorUpdate, update_contractor
    from contracts.contractor import ContractorProfile
    from rag.contractor_context import upsert_contractor

    await upsert_contractor(
        ContractorProfile(id="c1", name="Acme", payment_terms="Net 30"), session
    )

    # Client sends an explicit null for a non-nullable field plus a real change.
    body = ContractorUpdate.model_validate({"payment_terms": None, "company": "Acme LLC"})
    updated = await update_contractor("c1", body, session=session)

    # Null is ignored (keeps prior value); the real change is applied.
    assert updated.payment_terms == "Net 30"
    assert updated.company == "Acme LLC"
    assert updated.name == "Acme"


@pytest.mark.asyncio
async def test_review_accepts_json_body(session):
    from app.api.routes import ReviewRequest, submit_review
    from harness.models import load_envelope, save_envelope

    env = _envelope_with_extraction()
    await save_envelope(env, session)

    result = await submit_review(
        env.id, ReviewRequest(verdict="approved", notes="looks good"), session=session
    )
    assert result["status"] == "approved"

    loaded = await load_envelope(env.id, session)
    assert loaded is not None
    assert loaded.status == "approved"
