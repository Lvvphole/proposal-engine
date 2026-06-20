"""API route definitions.

All HTTP endpoints for the proposal engine.
"""

from __future__ import annotations

import base64

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.envelope import Envelope, EnvelopeStatus
from contracts.events import DomainEvent, EventKind
from core.db import get_session
from harness.models import list_envelopes, load_envelope, save_envelope

logger = structlog.get_logger()
router = APIRouter()


class SubmitQuoteResponse(BaseModel):
    envelope_id: str
    status: str
    message: str


class EnvelopeStatusResponse(BaseModel):
    envelope_id: str
    status: str
    line_item_count: int | None = None
    total: str | None = None
    quality_score: float | None = None


@router.post("/quotes", response_model=SubmitQuoteResponse)
async def submit_quote(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    contractor_id: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
):
    """Submit a supplier quote document for processing."""
    content = await file.read()
    content_b64 = base64.b64encode(content).decode()

    envelope = Envelope(
        source_filename=file.filename or "unknown",
        source_content_type=file.content_type or "application/octet-stream",
        source_bytes_b64=content_b64,
        contractor_id=contractor_id,
    )

    await save_envelope(envelope, session)
    background_tasks.add_task(_dispatch_pipeline, envelope.id)

    return SubmitQuoteResponse(
        envelope_id=envelope.id,
        status=envelope.status,
        message=f"Quote '{file.filename}' received. Processing queued.",
    )


async def _dispatch_pipeline(envelope_id: str) -> None:
    """Background task: load envelope and run through orchestrator."""
    from core.db import _get_session_factory
    from pipelines.orchestrator import process_envelope

    async with _get_session_factory()() as session:
        envelope = await load_envelope(envelope_id, session)
        if envelope is None:
            logger.error("dispatch_envelope_not_found", envelope_id=envelope_id)
            return
        try:
            envelope = await process_envelope(envelope)
            await save_envelope(envelope, session)
        except Exception as exc:
            logger.error("dispatch_failed", envelope_id=envelope_id, error=str(exc))


@router.get("/quotes/{envelope_id}", response_model=EnvelopeStatusResponse)
async def get_quote_status(
    envelope_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Check the processing status of a submitted quote."""
    envelope = await load_envelope(envelope_id, session)
    if envelope is None:
        raise HTTPException(status_code=404, detail=f"Envelope {envelope_id!r} not found")

    line_item_count = None
    total = None
    quality_score = None

    if envelope.extraction is not None:
        line_item_count = envelope.extraction.line_item_count
        if envelope.extraction.totals and envelope.extraction.totals.total is not None:
            total = str(envelope.extraction.totals.total)
        quality_score = envelope.extraction.quality_score

    return EnvelopeStatusResponse(
        envelope_id=envelope.id,
        status=envelope.status,
        line_item_count=line_item_count,
        total=total,
        quality_score=quality_score,
    )


@router.get("/quotes")
async def list_quotes(
    status: str | None = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """List recent quote submissions with optional status filter."""
    envelopes = await list_envelopes(session, status=status, limit=limit)
    return {
        "quotes": [
            {"envelope_id": e.id, "status": e.status, "filename": e.source_filename}
            for e in envelopes
        ],
        "total": len(envelopes),
    }


@router.post("/quotes/{envelope_id}/review")
async def submit_review(
    envelope_id: str,
    verdict: str,
    notes: str = "",
    session: AsyncSession = Depends(get_session),
):
    """Submit a human review decision for a proposal."""
    from contracts.review import ReviewVerdict
    from core import message_bus

    if verdict not in [v.value for v in ReviewVerdict]:
        raise HTTPException(status_code=400, detail=f"Invalid verdict: {verdict}")

    envelope = await load_envelope(envelope_id, session)
    if envelope is None:
        raise HTTPException(status_code=404, detail=f"Envelope {envelope_id!r} not found")

    if envelope.status != EnvelopeStatus.REVIEW_PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Envelope is in status {envelope.status!r}, not review_pending",
        )

    if verdict == ReviewVerdict.APPROVED:
        new_status = EnvelopeStatus.APPROVED
        event_kind = EventKind.REVIEW_APPROVED
    elif verdict == ReviewVerdict.REJECTED:
        new_status = EnvelopeStatus.REJECTED
        event_kind = EventKind.REVIEW_REJECTED
    else:
        new_status = EnvelopeStatus.REVIEW_PENDING
        event_kind = EventKind.REVIEW_REQUESTED

    envelope.advance(
        new_status,
        DomainEvent(kind=event_kind, agent="review_api", detail=notes or ""),
    )

    await save_envelope(envelope, session)

    await message_bus.publish(
        DomainEvent(
            kind=event_kind,
            agent="review_api",
            metadata={"envelope_id": envelope_id, "verdict": verdict},
        )
    )

    return {
        "envelope_id": envelope_id,
        "verdict": verdict,
        "status": envelope.status,
        "message": "Review recorded.",
    }
