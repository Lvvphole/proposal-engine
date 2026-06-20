"""Hook registry — before/after hooks for pipeline events, with PII redaction."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

logger = structlog.get_logger()

Hook = Callable[[str, dict[str, Any]], Awaitable[None]]

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b(\+?1[\s.\-]?)?(\(?\d{3}\)?[\s.\-]?)(\d{3}[\s.\-]?\d{4})\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+(?:[A-Za-z0-9#.,-]+\s+){1,5}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court)\b",
    re.IGNORECASE,
)


def redact_pii(text: str) -> str:
    """Replace PII patterns with placeholders."""
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    text = _SSN_RE.sub("[SSN]", text)
    text = _ADDRESS_RE.sub("[ADDRESS]", text)
    return text


class HookRegistry:
    """Registry for before/after hooks on pipeline events."""

    def __init__(self) -> None:
        self._before: list[Hook] = []
        self._after: list[Hook] = []

    def register_before_hook(self, hook: Hook) -> None:
        self._before.append(hook)

    def register_after_hook(self, hook: Hook) -> None:
        self._after.append(hook)

    async def run_before_hooks(self, event: str, context: dict[str, Any]) -> None:
        for hook in self._before:
            try:
                await hook(event, context)
            except Exception as exc:
                logger.warning(
                    "before_hook_failed", hook=hook.__name__, event=event, error=str(exc)
                )

    async def run_after_hooks(self, event: str, context: dict[str, Any]) -> None:
        for hook in self._after:
            try:
                await hook(event, context)
            except Exception as exc:
                logger.warning("after_hook_failed", hook=hook.__name__, event=event, error=str(exc))


async def pii_redaction_hook(event: str, context: dict[str, Any]) -> None:
    """Redact PII from any string values in the context dict."""
    for key, value in list(context.items()):
        if isinstance(value, str):
            context[key] = redact_pii(value)


async def audit_logging_hook(event: str, context: dict[str, Any]) -> None:
    """Log every pipeline event for audit purposes."""
    logger.info(
        "pipeline_event",
        event=event,
        **{k: v for k, v in context.items() if k != "source_bytes_b64"},
    )


def install_default_hooks(registry: HookRegistry) -> None:
    """Register the standard set of hooks onto a registry."""
    registry.register_before_hook(pii_redaction_hook)
    registry.register_after_hook(audit_logging_hook)


_default_registry = HookRegistry()
install_default_hooks(_default_registry)
