"""Tests for the contractor preference engine (DB-backed)."""

from __future__ import annotations

import os

import pytest


@pytest.fixture
async def db_session(tmp_path):
    db_file = tmp_path / "contractors.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    from core.config import get_config

    get_config.cache_clear()
    from core.db import _get_session_factory, init_db, reset_engine

    reset_engine()
    await init_db()
    async with _get_session_factory()() as session:
        yield session
    reset_engine()
    get_config.cache_clear()
    os.environ["DATABASE_URL"] = "sqlite:///./test_proposals.db"


@pytest.mark.asyncio
async def test_upsert_and_load_roundtrip(db_session):
    from contracts.contractor import ContractorProfile
    from rag.contractor_context import get_profile, upsert_contractor

    profile = ContractorProfile(id="c1", name="Acme Builders", company="Acme LLC")
    await upsert_contractor(profile, db_session)

    loaded = await get_profile("c1", db_session)
    assert loaded is not None
    assert loaded.name == "Acme Builders"
    assert loaded.company == "Acme LLC"
    assert loaded.default_markup_pct == 0.20


@pytest.mark.asyncio
async def test_get_context_known_contractor_merges_markups(db_session):
    from contracts.contractor import ContractorProfile
    from rag.contractor_context import get_context, upsert_contractor

    profile = ContractorProfile(
        id="c2",
        name="Bright Homes",
        default_markup_pct=0.30,
        category_markups={"lumber": 0.15},
        payment_terms="Net 30",
    )
    await upsert_contractor(profile, db_session)

    ctx = await get_context("c2", db_session)
    assert ctx["contractor_id"] == "c2"
    assert ctx["markup_rules"] == {"default_pct": 0.30, "lumber": 0.15}
    assert ctx["payment_terms"] == "Net 30"


@pytest.mark.asyncio
async def test_get_context_unknown_returns_defaults(db_session):
    from rag.contractor_context import get_context

    ctx = await get_context("ghost", db_session)
    assert ctx["contractor_id"] == "ghost"
    assert ctx["markup_rules"] == {"default_pct": 0.20}
    assert ctx["payment_terms"] == "Due on completion"
    assert ctx["history_summary"] == "No prior proposals on file."


@pytest.mark.asyncio
async def test_upsert_updates_existing(db_session):
    from contracts.contractor import ContractorProfile
    from rag.contractor_context import get_profile, upsert_contractor

    await upsert_contractor(ContractorProfile(id="c3", name="Original"), db_session)
    await upsert_contractor(
        ContractorProfile(id="c3", name="Renamed", default_markup_pct=0.25), db_session
    )

    loaded = await get_profile("c3", db_session)
    assert loaded is not None
    assert loaded.name == "Renamed"
    assert loaded.default_markup_pct == 0.25


@pytest.mark.asyncio
async def test_list_contractors(db_session):
    from contracts.contractor import ContractorProfile
    from rag.contractor_context import list_contractors, upsert_contractor

    for i in range(3):
        await upsert_contractor(ContractorProfile(id=f"c{i}", name=f"Co {i}"), db_session)

    profiles = await list_contractors(db_session)
    assert {p.id for p in profiles} == {"c0", "c1", "c2"}


def test_markup_rules_helper():
    from contracts.contractor import ContractorProfile

    p = ContractorProfile(id="x", name="N", default_markup_pct=0.2, category_markups={"steel": 0.1})
    assert p.markup_rules() == {"default_pct": 0.2, "steel": 0.1}
