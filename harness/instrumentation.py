"""Metrics and counters for operational monitoring.

Lightweight in-process metrics.  In production, these would export
to Prometheus / Datadog / CloudWatch via a background thread.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager

import structlog

logger = structlog.get_logger()

_counters: dict[str, int] = defaultdict(int)
_histograms: dict[str, list[float]] = defaultdict(list)


def increment(name: str, value: int = 1) -> None:
    _counters[name] += value


@contextmanager
def timer(name: str) -> Iterator[None]:
    """Context manager that records elapsed time to a histogram."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    _histograms[name].append(elapsed)
    logger.debug("timer", name=name, elapsed_ms=round(elapsed * 1000, 2))


def get_counter(name: str) -> int:
    return _counters[name]


def get_histogram(name: str) -> list[float]:
    return list(_histograms[name])


def reset() -> None:
    """Reset all metrics.  Used in tests."""
    _counters.clear()
    _histograms.clear()
