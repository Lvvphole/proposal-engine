"""In-process message bus for domain events.

Lightweight pub/sub so that components can react to pipeline events
without direct coupling.  Handlers register for EventKind values;
when an event is published, all matching handlers fire.

This is intentionally simple — no external broker.  If we need
cross-process eventing later, swap this for a Redis Streams or
NATS adapter behind the same interface.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable

import structlog

from contracts.events import DomainEvent, EventKind

logger = structlog.get_logger()

Handler = Callable[[DomainEvent], Awaitable[None]]

_handlers: dict[EventKind, list[Handler]] = defaultdict(list)


def subscribe(kind: EventKind, handler: Handler) -> None:
    """Register a handler for a specific event kind."""
    _handlers[kind].append(handler)
    logger.debug("handler_subscribed", kind=kind, handler=handler.__name__)


async def publish(event: DomainEvent) -> None:
    """Publish an event to all registered handlers.

    Handlers run concurrently.  Failures are logged but don't block
    other handlers or the caller.
    """
    handlers = _handlers.get(event.kind, [])
    if not handlers:
        return

    logger.info("event_published", kind=event.kind, handler_count=len(handlers))

    results = await asyncio.gather(
        *(h(event) for h in handlers),
        return_exceptions=True,
    )

    for handler, result in zip(handlers, results):
        if isinstance(result, Exception):
            logger.error(
                "handler_failed",
                handler=handler.__name__,
                event_kind=event.kind,
                error=str(result),
            )


def clear() -> None:
    """Remove all handlers.  Used in tests."""
    _handlers.clear()
