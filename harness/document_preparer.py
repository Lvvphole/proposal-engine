"""Document preparation — token counting, compression, and preflight checks."""

from __future__ import annotations

import json
from pathlib import Path

from contracts.errors import ContextWindowExceededError

_POLICY_PATH = Path(__file__).parent.parent / "policies" / "compression_policy.json"
_policy_cache: dict | None = None


def _load_policy() -> dict:
    global _policy_cache
    if _policy_cache is None:
        _policy_cache = json.loads(_POLICY_PATH.read_text())
    return _policy_cache


def count_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses tiktoken if available, otherwise falls back to len(text) // 4.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


def prepare_document(content: str, *, content_type: str = "text/plain") -> str:
    """Prepare document content for LLM input, applying compression policy.

    Truncates to max_input_chars, keeping the first and last portions
    if the document exceeds the limit (page-aware for text content).
    """
    policy = _load_policy()
    rules = policy.get("rules", {})
    max_chars: int = rules.get("max_input_chars", 100_000)

    if len(content) <= max_chars:
        return content

    strategy = rules.get("truncation_strategy", "keep_first_and_last_pages")

    if strategy == "keep_first_and_last_pages":
        half = max_chars // 2
        first_part = content[:half]
        last_part = content[-half:]
        omitted = len(content) - max_chars
        return (
            f"{first_part}\n\n"
            f"[... {omitted} characters omitted by compression policy ...]\n\n"
            f"{last_part}"
        )

    return content[:max_chars]


def preflight_check(content: str, model_id: str) -> None:
    """Raise ContextWindowExceededError if content is too large for the model.

    Uses model_capabilities registry to get the context window size.
    """
    from harness.model_capabilities import get_capabilities

    try:
        caps = get_capabilities(model_id)
        context_window = caps.context_window
    except KeyError:
        context_window = 200_000

    token_count = count_tokens(content)
    # Leave 10% headroom for system prompt + response
    effective_limit = int(context_window * 0.9)

    if token_count > effective_limit:
        raise ContextWindowExceededError(
            f"Document requires ~{token_count} tokens but model {model_id!r} "
            f"effective limit is {effective_limit}",
            context={
                "token_count": token_count,
                "effective_limit": effective_limit,
                "model_id": model_id,
            },
        )


def _reset_cache() -> None:
    """Reset policy cache. For tests."""
    global _policy_cache
    _policy_cache = None
