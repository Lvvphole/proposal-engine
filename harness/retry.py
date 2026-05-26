"""Retry orchestration for agent failures.

Wraps tenacity with pipeline-specific policies:
- Extraction failures: up to 3 retries with exponential backoff
- Classification failures: 2 retries then escalate to Pipeline C fallback
- Budget failures: no retry, immediate escalation
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TypeVar

import structlog
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from contracts.errors import (
    BudgetExceededError,
    ExtractionError,
    RecoveryExhaustedError,
)

logger = structlog.get_logger()
T = TypeVar("T")


async def with_extraction_retry(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    max_attempts: int = 3,
    **kwargs: Any,
) -> T:
    """Retry an extraction call with exponential backoff.

    Budget errors are never retried — they propagate immediately.
    """
    attempt = 0
    last_error: Exception | None = None

    while attempt < max_attempts:
        try:
            return await fn(*args, **kwargs)
        except BudgetExceededError:
            raise  # Never retry budget failures
        except ExtractionError as e:
            attempt += 1
            last_error = e
            logger.warning(
                "extraction_retry",
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(e),
            )
            if attempt >= max_attempts:
                break

    raise RecoveryExhaustedError(
        f"Extraction failed after {max_attempts} attempts: {last_error}",
        context={"attempts": max_attempts},
    )


async def with_classification_retry(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Retry classification up to 2 times, then signal fallback needed."""
    try:
        return await with_extraction_retry(fn, *args, max_attempts=2, **kwargs)
    except RecoveryExhaustedError:
        logger.warning("classification_exhausted_falling_back_to_pipeline_c")
        raise
