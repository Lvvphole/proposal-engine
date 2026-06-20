"""Tests for Supabase JWT auth + per-user tenancy scoping."""

from __future__ import annotations

import os
import time

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.auth import DEV_PRINCIPAL, Principal, get_current_principal

_SECRET = "testsecret"


def _request(token: str | None) -> Request:
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request(
        {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b""}
    )


def _token(
    *,
    secret: str = _SECRET,
    sub: str = "user-123",
    aud: str = "authenticated",
    exp_offset: int = 3600,
):
    payload = {
        "sub": sub,
        "aud": aud,
        "email": "user@example.com",
        "role": "authenticated",
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def enable_auth():
    from core.config import get_config

    prev_enabled = os.environ.get("AUTH_ENABLED")
    prev_secret = os.environ.get("SUPABASE_JWT_SECRET")
    os.environ["AUTH_ENABLED"] = "true"
    os.environ["SUPABASE_JWT_SECRET"] = _SECRET
    get_config.cache_clear()
    yield _SECRET
    for key, prev in (("AUTH_ENABLED", prev_enabled), ("SUPABASE_JWT_SECRET", prev_secret)):
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev
    get_config.cache_clear()


# ── Auth dependency ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disabled_returns_dev_principal():
    from core.config import get_config

    os.environ["AUTH_ENABLED"] = "false"
    get_config.cache_clear()
    try:
        principal = await get_current_principal(_request(None))
        assert principal == DEV_PRINCIPAL
    finally:
        os.environ.pop("AUTH_ENABLED", None)
        get_config.cache_clear()


@pytest.mark.asyncio
async def test_valid_token_yields_principal(enable_auth):
    principal = await get_current_principal(_request(_token(sub="user-abc")))
    assert principal.user_id == "user-abc"
    assert principal.email == "user@example.com"


@pytest.mark.asyncio
async def test_missing_header_401(enable_auth):
    with pytest.raises(HTTPException) as exc:
        await get_current_principal(_request(None))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_bad_signature_401(enable_auth):
    with pytest.raises(HTTPException) as exc:
        await get_current_principal(_request(_token(secret="wrong-secret")))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_401(enable_auth):
    with pytest.raises(HTTPException) as exc:
        await get_current_principal(_request(_token(exp_offset=-10)))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_wrong_audience_401(enable_auth):
    with pytest.raises(HTTPException) as exc:
        await get_current_principal(_request(_token(aud="some-other-aud")))
    assert exc.value.status_code == 401


# ── Tenancy scoping ──────────────────────────────────────────────────────


@pytest.fixture
async def session(tmp_path):
    db_file = tmp_path / "auth.db"
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


@pytest.mark.asyncio
async def test_quotes_scoped_to_owner(session, enable_auth):
    from app.api.routes import get_quote_status, list_quotes
    from contracts.envelope import Envelope
    from harness.models import save_envelope

    alice = Principal(user_id="user-A")
    ea = Envelope(source_filename="a.pdf", owner_id="user-A")
    eb = Envelope(source_filename="b.pdf", owner_id="user-B")
    await save_envelope(ea, session)
    await save_envelope(eb, session)

    listed = await list_quotes(session=session, principal=alice)
    assert {q["envelope_id"] for q in listed["quotes"]} == {ea.id}

    # Alice cannot read Bob's envelope (404, not 403 — don't leak existence).
    with pytest.raises(HTTPException) as exc:
        await get_quote_status(eb.id, session=session, principal=alice)
    assert exc.value.status_code == 404

    own = await get_quote_status(ea.id, session=session, principal=alice)
    assert own.envelope_id == ea.id


@pytest.mark.asyncio
async def test_contractors_scoped_to_owner(session, enable_auth):
    from app.api.contractors import (
        ContractorCreate,
        create_contractor,
        list_all_contractors,
        read_contractor,
    )

    alice = Principal(user_id="user-A")
    bob = Principal(user_id="user-B")
    ca = await create_contractor(ContractorCreate(name="ACo"), session=session, principal=alice)
    cb = await create_contractor(ContractorCreate(name="BCo"), session=session, principal=bob)

    assert ca.owner_id == "user-A"
    listed = await list_all_contractors(session=session, principal=alice)
    assert {c.id for c in listed} == {ca.id}

    with pytest.raises(HTTPException) as exc:
        await read_contractor(cb.id, session=session, principal=alice)
    assert exc.value.status_code == 404
