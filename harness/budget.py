"""Budget enforcement for LLM spend.

Two limits enforced:
1. Per-envelope: no single quote processing exceeds BUDGET_PER_ENVELOPE_LIMIT_USD
2. Daily aggregate: total spend across all envelopes cannot exceed BUDGET_DAILY_LIMIT_USD

Token-to-cost conversion uses conservative estimates.  Prices update
when model routing policy changes.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import structlog

from contracts.envelope import Envelope
from contracts.errors import BudgetExceededError
from core.config import get_config

logger = structlog.get_logger()

# Conservative $/1K-token estimates (input, output) by model family
_COST_PER_1K: dict[str, tuple[Decimal, Decimal]] = {
    "claude-sonnet-4-20250514": (Decimal("0.003"), Decimal("0.015")),
    "claude-haiku-3-5-20241022": (Decimal("0.0008"), Decimal("0.004")),
}
_DEFAULT_COST = (Decimal("0.003"), Decimal("0.015"))

# Daily accumulator (resets at midnight UTC)
_daily_spend: dict[str, Decimal] = {}  # date-string → total USD


def _estimate_cost(input_tokens: int, output_tokens: int, model: str) -> Decimal:
    input_rate, output_rate = _COST_PER_1K.get(model, _DEFAULT_COST)
    return (
        Decimal(input_tokens) / 1000 * input_rate
        + Decimal(output_tokens) / 1000 * output_rate
    )


def estimate_envelope_cost(envelope: Envelope, model: str = "") -> Decimal:
    """Estimate total cost accumulated on an envelope so far."""
    total_input = sum(
        v for k, v in envelope.token_usage.items() if k.endswith("_input")
    )
    total_output = sum(
        v for k, v in envelope.token_usage.items() if k.endswith("_output")
    )
    return _estimate_cost(total_input, total_output, model)


def check_budget(envelope: Envelope, model: str = "") -> None:
    """Raise BudgetExceededError if limits would be breached."""
    config = get_config()

    envelope_cost = estimate_envelope_cost(envelope, model)
    if envelope_cost > config.budget_per_envelope_limit_usd:
        raise BudgetExceededError(
            f"Envelope {envelope.id} cost ${envelope_cost} exceeds "
            f"per-envelope limit ${config.budget_per_envelope_limit_usd}",
            context={"envelope_id": envelope.id, "cost": str(envelope_cost)},
        )

    today = datetime.now(timezone.utc).date().isoformat()
    daily_total = _daily_spend.get(today, Decimal("0")) + envelope_cost
    if daily_total > config.budget_daily_limit_usd:
        raise BudgetExceededError(
            f"Daily spend ${daily_total} would exceed limit ${config.budget_daily_limit_usd}",
            context={"daily_total": str(daily_total)},
        )


def record_spend(amount: Decimal) -> None:
    """Record spend against the daily accumulator."""
    today = datetime.now(timezone.utc).date().isoformat()
    _daily_spend[today] = _daily_spend.get(today, Decimal("0")) + amount
    logger.info("spend_recorded", amount=str(amount), daily_total=str(_daily_spend[today]))
