"""Streaming LLM calls and SSE event bridge."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import structlog
from anthropic import AsyncAnthropic

from core.config import get_config

logger = structlog.get_logger()

_envelope_queues: dict[str, list[asyncio.Queue]] = {}


async def call_llm_streaming(
    *,
    system: str,
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    agent_name: str = "unknown",
) -> AsyncIterator[str]:
    """Stream text deltas from the LLM using client.messages.stream().

    Yields text delta strings as they arrive.
    """
    config = get_config()
    model = model or config.default_model
    max_tokens = max_tokens or config.max_tokens

    client = AsyncAnthropic(api_key=config.anthropic_api_key)

    logger.info("llm_streaming_start", agent=agent_name, model=model)

    async with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text

    logger.info("llm_streaming_complete", agent=agent_name, model=model)


class SSEBridge:
    """Bridges the message bus to per-envelope SSE queues.

    Call SSEBridge.install() at startup to subscribe to all domain events.
    Consumers call SSEBridge.subscribe(envelope_id) to get a queue of
    SSE-formatted event strings.
    """

    _installed: bool = False

    @classmethod
    def install(cls) -> None:
        """Register the bridge as a message bus handler."""
        if cls._installed:
            return
        from contracts.events import EventKind
        from core import message_bus

        async def _handler(event) -> None:
            envelope_id = event.metadata.get("envelope_id") if event.metadata else None
            if envelope_id is None:
                return
            queues = _envelope_queues.get(envelope_id, [])
            payload = json.dumps({"kind": event.kind, "metadata": event.metadata or {}})
            sse_line = f"data: {payload}\n\n"
            for q in queues:
                await q.put(sse_line)

        for kind in EventKind:
            message_bus.subscribe(kind, _handler)

        cls._installed = True

    @classmethod
    def subscribe(cls, envelope_id: str) -> asyncio.Queue:
        """Return a queue that will receive SSE lines for the given envelope."""
        q: asyncio.Queue = asyncio.Queue()
        _envelope_queues.setdefault(envelope_id, []).append(q)
        return q

    @classmethod
    def unsubscribe(cls, envelope_id: str, queue: asyncio.Queue) -> None:
        queues = _envelope_queues.get(envelope_id, [])
        if queue in queues:
            queues.remove(queue)

    @classmethod
    def reset(cls) -> None:
        """Clear all subscriptions. For tests."""
        _envelope_queues.clear()
        cls._installed = False


async def sse_event_generator(
    envelope_id: str,
    *,
    timeout: float = 30.0,
) -> AsyncIterator[str]:
    """Yield SSE-formatted event strings for the given envelope.

    Yields a heartbeat comment every ~15 seconds to keep connections alive.
    Terminates after ``timeout`` seconds of inactivity.
    """
    queue = SSEBridge.subscribe(envelope_id)
    try:
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield line
                if '"approved"' in line or '"rejected"' in line:
                    break
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        SSEBridge.unsubscribe(envelope_id, queue)
