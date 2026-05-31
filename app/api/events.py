"""SSE event stream endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.streaming import sse_event_generator

events_router = APIRouter()


@events_router.get("/events/{envelope_id}")
async def stream_envelope_events(envelope_id: str) -> StreamingResponse:
    """Stream Server-Sent Events for a specific envelope's lifecycle."""
    return StreamingResponse(
        sse_event_generator(envelope_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
