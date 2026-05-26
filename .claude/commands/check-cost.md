# /check-cost

Check token usage and cost for a specific envelope or the current day.

## Usage

```
/check-cost                    # Show today's daily budget usage
/check-cost <envelope_id>      # Show cost breakdown for a specific envelope
```

## Steps

1. Read `harness/budget.py` to understand the budget tracking interface.
2. If an envelope ID is provided:
   - Load the envelope's token usage from the audit log
   - Compute cost per agent using rates from `policies/budget_policy.json`
   - Show breakdown: classifier, header extractor, line item extractor, totals extractor, recovery (if any)
   - Show total cost vs. per-envelope limit ($2.00)
3. If no envelope ID:
   - Sum all envelope costs from today's audit log
   - Show total daily cost vs. daily limit ($25.00)
   - Show count of envelopes processed today
   - Show average cost per envelope

## Output Format

```
Envelope abc123 — Cost Breakdown
─────────────────────────────────
Classifier (Haiku):       $0.001  (800 in / 200 out)
Header Extractor:         $0.014  (2,000 in / 500 out)
Line Item Extractor:      $0.042  (4,000 in / 2,000 out)
Totals Extractor:         $0.009  (1,500 in / 300 out)
─────────────────────────────────
Total:                    $0.066  (3.3% of $2.00 limit)
```
