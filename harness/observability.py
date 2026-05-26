"""Structured logging and trace context propagation.

Configures structlog for the entire application.  All modules use
`structlog.get_logger()` — this module ensures they get the right
processors.
"""

from __future__ import annotations

import uuid

import structlog


def setup_logging(*, json_output: bool = True, level: str = "INFO") -> None:
    """Configure structlog for the application."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def new_trace_id() -> str:
    """Generate a new trace ID for request correlation."""
    return str(uuid.uuid4())
