"""Policy gate — enforces tool permission and human review policies."""

from __future__ import annotations

import json
import time
from pathlib import Path

from contracts.errors import PolicyViolationError

_POLICY_DIR = Path(__file__).parent.parent / "policies"

_tool_policy_cache: dict | None = None
_review_policy_cache: dict | None = None
_rate_limit_counters: dict[str, list[float]] = {}


def _load_tool_policy() -> dict:
    global _tool_policy_cache
    if _tool_policy_cache is None:
        path = _POLICY_DIR / "tool_permission_policy.json"
        _tool_policy_cache = json.loads(path.read_text())
    return _tool_policy_cache


def _load_review_policy() -> dict:
    global _review_policy_cache
    if _review_policy_cache is None:
        path = _POLICY_DIR / "human_review_policy.json"
        _review_policy_cache = json.loads(path.read_text())
    return _review_policy_cache


def check_tool_policy(tool_name: str, *, require_auth: bool = False) -> dict:
    """Check whether a tool call is permitted.

    Returns the tool's policy dict if permitted.
    Raises PolicyViolationError if auth_required and require_auth=False,
    or if the rate limit per hour has been exceeded.
    """
    policy = _load_tool_policy()
    tools = policy.get("tools", {})

    tool_cfg = tools.get(tool_name, {})
    auth_required = tool_cfg.get("auth_required", False)

    if auth_required and not require_auth:
        raise PolicyViolationError(
            f"Tool '{tool_name}' requires authentication",
            context={"tool": tool_name, "auth_required": True},
        )

    rate_limit = tool_cfg.get("rate_limit_per_hour")
    if rate_limit is not None:
        now = time.monotonic()
        window = 3600.0
        calls = _rate_limit_counters.get(tool_name, [])
        calls = [t for t in calls if now - t < window]
        if len(calls) >= rate_limit:
            raise PolicyViolationError(
                f"Tool '{tool_name}' rate limit ({rate_limit}/hr) exceeded",
                context={"tool": tool_name, "rate_limit_per_hour": rate_limit},
            )
        calls.append(now)
        _rate_limit_counters[tool_name] = calls

    return tool_cfg


def check_human_review_required(envelope: object) -> bool:
    """Return True if the envelope's current state requires human review.

    Checks against the triggers defined in human_review_policy.json.
    """
    policy = _load_review_policy()
    triggers = policy.get("triggers", {})

    always_triggers = triggers.get("always", [])
    if "proposal_delivery" in always_triggers:
        status = getattr(envelope, "status", None)
        if status in ("review_pending", "approved"):
            return True

    conditional = triggers.get("conditional", {})

    extraction = getattr(envelope, "extraction", None)
    if extraction is not None:
        quality_score = getattr(extraction, "quality_score", None)
        threshold = conditional.get("quality_score_below")
        if quality_score is not None and threshold is not None:
            if quality_score < threshold:
                return True

        confidence = getattr(extraction, "extraction_confidence", None)
        conf_threshold = conditional.get("confidence_below")
        if confidence is not None and conf_threshold is not None:
            if confidence < conf_threshold:
                return True

    return False


def _reset_caches() -> None:
    """Reset policy caches and rate limit counters. For tests only."""
    global _tool_policy_cache, _review_policy_cache
    _tool_policy_cache = None
    _review_policy_cache = None
    _rate_limit_counters.clear()
