"""Tests for the proposal HTML renderer + document endpoint."""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from contracts.contractor import ContractorProfile
from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData
from pipelines.proposal_builder import build_proposal
from pipelines.proposal_renderer import render_proposal_html


def _proposal(contractor: ContractorProfile):
    extraction = ExtractionResult(
        header=HeaderData(supplier_name="ABC Supply", delivery_terms="FOB Origin"),
        line_items=[
            LineItem(
                description="CDX Plywood",
                quantity=Decimal("2"),
                unit_price=Decimal("10.00"),
                extended_price=Decimal("20.00"),
            )
        ],
        totals=TotalsData(subtotal=Decimal("20.00"), tax_rate=Decimal("0.10")),
        source_pipeline="a",
    )
    return build_proposal(extraction, contractor)


def test_render_includes_customer_facing_fields():
    contractor = ContractorProfile(
        id="c1", name="Jane Doe", company="Doe Construction", default_markup_pct=0.25
    )
    html = render_proposal_html(_proposal(contractor), contractor)

    assert html.startswith("<!doctype html>")
    assert "Doe Construction" in html
    assert "CDX Plywood" in html
    # 20.00 cost + 25% markup → 25.00 subtotal; 10% tax → 2.50; total 27.50.
    assert "$25.00" in html
    assert "$27.50" in html
    assert "Tax (10%)" in html


def test_render_hides_internal_margin():
    contractor = ContractorProfile(id="c1", name="N", company="Co", default_markup_pct=0.25)
    html = render_proposal_html(_proposal(contractor), contractor)
    # The internal-margin section and supplier cost figures must NOT leak into
    # the customer doc. Supplier unit/extended are $10.00 / $20.00; the customer
    # sees the marked-up $12.50 / $25.00.
    assert "Supplier cost" not in html
    assert "Markup" not in html
    assert "$10.00" not in html
    assert "$20.00" not in html
    assert "$12.50" in html


def test_render_escapes_html():
    contractor = ContractorProfile(id="c1", name="N", company="A & B <Co>", default_markup_pct=0.1)
    html = render_proposal_html(_proposal(contractor), contractor)
    assert "A &amp; B &lt;Co&gt;" in html
    assert "<Co>" not in html


def test_render_without_contractor_uses_generic_header():
    contractor = ContractorProfile(id="default", name="(default)", default_markup_pct=0.2)
    html = render_proposal_html(_proposal(contractor), None)
    assert "<h1>Proposal</h1>" in html


# ── Endpoint ─────────────────────────────────────────────────────────────


@pytest.fixture
async def session(tmp_path):
    db_file = tmp_path / "renderer.db"
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


def _envelope_with_proposal():
    from contracts.envelope import Envelope, EnvelopeStatus
    from contracts.events import DomainEvent, EventKind

    contractor = ContractorProfile(id="c1", name="N", company="Doe Construction")
    env = Envelope(source_filename="q.pdf", contractor_id="c1")
    env.proposal = _proposal(contractor)
    env.advance(
        EnvelopeStatus.REVIEW_PENDING,
        DomainEvent(kind=EventKind.PROPOSAL_GENERATED, agent="test"),
    )
    return env


@pytest.mark.asyncio
async def test_document_endpoint_returns_html(session):
    from app.api.routes import get_proposal_document
    from harness.models import save_envelope
    from rag.contractor_context import upsert_contractor

    # The endpoint loads the contractor from the DB for the letterhead.
    await upsert_contractor(
        ContractorProfile(id="c1", name="N", company="Doe Construction"), session
    )
    env = _envelope_with_proposal()
    await save_envelope(env, session)

    response = await get_proposal_document(env.id, session=session)
    assert response.status_code == 200
    assert response.media_type == "text/html"
    assert b"Doe Construction" in response.body


@pytest.mark.asyncio
async def test_document_endpoint_409_without_proposal(session):
    from fastapi import HTTPException

    from app.api.routes import get_proposal_document
    from contracts.envelope import Envelope
    from harness.models import save_envelope

    env = Envelope(source_filename="raw.pdf")
    await save_envelope(env, session)

    with pytest.raises(HTTPException) as exc:
        await get_proposal_document(env.id, session=session)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_document_endpoint_404_unknown(session):
    from fastapi import HTTPException

    from app.api.routes import get_proposal_document

    with pytest.raises(HTTPException) as exc:
        await get_proposal_document("nope", session=session)
    assert exc.value.status_code == 404
