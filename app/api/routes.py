"""API route definitions.

All HTTP endpoints for the proposal engine.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from contracts.envelope import Envelope, EnvelopeStatus

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
    file: UploadFile = File(...),
    contractor_id: str | None = Form(None),
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

    # TODO: dispatch to orchestrator asynchronously via task queue
    # For now, return the envelope ID for polling

    return SubmitQuoteResponse(
        envelope_id=envelope.id,
        status=envelope.status,
        message=f"Quote '{file.filename}' received. Processing queued.",
    )


@router.get("/quotes/{envelope_id}", response_model=EnvelopeStatusResponse)
async def get_quote_status(envelope_id: str):
    """Check the processing status of a submitted quote."""
    # TODO: look up envelope from database
    # Placeholder response
    return EnvelopeStatusResponse(
        envelope_id=envelope_id,
        status="review_pending",
    )


@router.get("/quotes")
async def list_quotes(
    status: str | None = None,
    limit: int = 20,
):
    """List recent quote submissions with optional status filter."""
    # TODO: query database
    return {"quotes": [], "total": 0}


@router.post("/quotes/{envelope_id}/review")
async def submit_review(envelope_id: str, verdict: str, notes: str = ""):
    """Submit a human review decision for a proposal."""
    from contracts.review import ReviewVerdict

    if verdict not in [v.value for v in ReviewVerdict]:
        raise HTTPException(status_code=400, detail=f"Invalid verdict: {verdict}")

    # TODO: update envelope in database and trigger downstream actions
    return {
        "envelope_id": envelope_id,
        "verdict": verdict,
        "message": "Review recorded.",
    }
