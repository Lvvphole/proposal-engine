"""OpenTelemetry tracing with a no-op fallback when OTel is not installed."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OTEL_AVAILABLE = False

_tracer = None
_provider = None


class NoOpSpan:
    """Minimal span shim used when OTel is unavailable or tracing is disabled."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_exception(self, exc: Exception) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self) -> NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def setup_tracing(service_name: str = "proposal-engine") -> None:
    """Initialize the OTel tracer. No-op if OTel SDK is not installed."""
    global _tracer, _provider
    if not _OTEL_AVAILABLE:
        return
    _provider = TracerProvider()
    trace.set_tracer_provider(_provider)
    _tracer = trace.get_tracer(service_name)


@contextmanager
def start_span(name: str, **attributes: Any) -> Generator[Any, None, None]:
    """Start a tracing span, yielding a no-op if OTel is unavailable."""
    if not _OTEL_AVAILABLE or _tracer is None:
        span: Any = NoOpSpan()
        yield span
        return

    with _tracer.start_as_current_span(name) as span:
        for k, v in attributes.items():
            span.set_attribute(k, str(v))
        yield span


def record_llm_call(
    span: Any,
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Attach LLM call metadata to a span."""
    span.set_attribute("llm.model", model)
    span.set_attribute("llm.input_tokens", input_tokens)
    span.set_attribute("llm.output_tokens", output_tokens)
    span.set_attribute("llm.total_tokens", input_tokens + output_tokens)


def record_error(span: Any, error: Exception) -> None:
    """Record an exception on a span."""
    span.record_exception(error)
    try:
        if _OTEL_AVAILABLE:
            from opentelemetry.trace import StatusCode

            span.set_status(StatusCode.ERROR, str(error))
    except Exception:
        pass
