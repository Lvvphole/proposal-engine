# ADR-003: Token Economics and Budget Model

**Status:** Accepted
**Date:** 2024-06-01
**Author:** Emory

## Context

Each supplier quote extraction requires multiple LLM calls. Without cost controls, a single malformed document could trigger unlimited retries and consume the entire daily API budget.

## Decision

Implement a two-tier budget system:

1. **Per-envelope ceiling:** $2.00 per document. Covers classification + extraction + up to 2 recovery attempts.
2. **Daily ceiling:** $25.00 across all envelopes. Prevents runaway costs from high-volume days.

## Cost Model

Based on Anthropic's published pricing:

| Agent | Model | Typical Input | Typical Output | Cost/Call |
|---|---|---|---|---|
| Classifier | Haiku | ~800 tokens | ~200 tokens | ~$0.001 |
| Header Extractor | Sonnet | ~2,000 tokens | ~500 tokens | ~$0.014 |
| Line Item Extractor | Sonnet | ~4,000 tokens | ~2,000 tokens | ~$0.042 |
| Totals Extractor | Sonnet | ~1,500 tokens | ~300 tokens | ~$0.009 |
| Recovery Agent | Sonnet | ~5,000 tokens | ~3,000 tokens | ~$0.060 |

**Typical Pipeline A envelope cost:** ~$0.07 (no recovery), ~$0.19 (with 2 recovery attempts)
**Pipeline C single-pass cost:** ~$0.10

The $2.00 per-envelope ceiling provides a 10x safety margin over typical costs.

## Enforcement

- `harness/budget.py` tracks token usage per envelope and per day
- The orchestrator checks budget *before* every LLM call
- Budget exhaustion triggers `BudgetExceededError` which the orchestrator never retries — it escalates to human review immediately
- Budget state persists in the envelope object and is logged to the audit trail

## Consequences

- Documents requiring >$2.00 of extraction (extremely long, heavily formatted) must be handled manually
- The daily limit caps throughput at roughly 300-350 envelopes/day under normal conditions
- Budget thresholds are tunable via `policies/budget_policy.json` without code changes

## SaaS Pricing Implication

At 8-10% of closed revenue on typical residential roofing jobs ($8K-$25K), the service earns $640-$2,500 per closed deal. Extraction cost of $0.07-$0.19 per quote yields margins above 99% on the AI cost component. The real cost is in customer acquisition and support.
