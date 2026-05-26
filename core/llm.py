"""LLM client wrapper with token tracking and budget enforcement.

Every LLM call in the system goes through this module.  It wraps the
Anthropic SDK with:
  - Automatic token counting and accumulation on the envelope
  - Budget checks before each call
  - Structured logging of every request/response
  - Retry with backoff via tenacity
"""

from __future__ import annotations

import structlog
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from contracts.envelope import Envelope
from contracts.errors import BudgetExceededError
from core.config import get_config

logger = structlog.get_logger()


def _get_client() -> AsyncAnthropic:
    config = get_config()
    return AsyncAnthropic(api_key=config.anthropic_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
async def call_llm(
    *,
    system: str,
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    envelope: Envelope | None = None,
    agent_name: str = "unknown",
) -> str:
    """Make a single LLM call with tracking.

    Args:
        system: System prompt.
        messages: Conversation messages.
        model: Override model (defaults to config.default_model).
        max_tokens: Override max tokens.
        envelope: If provided, token usage is accumulated here.
        agent_name: Name of the calling agent (for logging/tracking).

    Returns:
        The assistant's text response.

    Raises:
        BudgetExceededError: If the call would exceed budget limits.
    """
    config = get_config()
    model = model or config.default_model
    max_tokens = max_tokens or config.max_tokens

    client = _get_client()

    logger.info(
        "llm_call_start",
        agent=agent_name,
        model=model,
        message_count=len(messages),
    )

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    if envelope is not None:
        key = f"{agent_name}_input"
        envelope.token_usage[key] = envelope.token_usage.get(key, 0) + input_tokens
        key = f"{agent_name}_output"
        envelope.token_usage[key] = envelope.token_usage.get(key, 0) + output_tokens

    logger.info(
        "llm_call_complete",
        agent=agent_name,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    text_blocks = [b.text for b in response.content if b.type == "text"]
    return "\n".join(text_blocks)
