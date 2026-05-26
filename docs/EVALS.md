# Evaluation Methodology

## Purpose

The eval framework measures extraction accuracy against labeled ground-truth data. It gates CI merges (no regressions allowed) and tracks improvement over time.

## Architecture

```
Golden Dataset (.jsonl)
        │
        ▼
   Eval Runner (run_evals.py)
        │
        ├── Runs input through relevant pipeline component
        ├── Scores output via judge functions
        │
        ▼
   Results compared to baseline.json
        │
        ├── PASS  →  PR may merge
        └── FAIL  →  PR blocked, regression details logged
```

## Eval Suites

| Suite | What It Tests | Golden File | Judge |
|---|---|---|---|
| `classifier` | Format detection + pipeline routing | `classifier_v1.jsonl` | Exact match on `format` and `pipeline` |
| `line_items` | Item extraction accuracy | `line_items_v1.jsonl` | `extraction_judge.score_line_items` — weighted: count 0.3, description match 0.4, price accuracy 0.3 |
| `recovery` | Recovery agent success on known failures | `recovery_v1.jsonl` | Before/after item count + error resolution |

## Golden Dataset Format

Each `.jsonl` file contains one test case per line:

```json
{
  "id": "cls-001",
  "input": "raw document text or reference",
  "expected": { "format": "structured_table", "pipeline": "a" },
  "tags": ["structured", "building-materials"]
}
```

Fields: `id` (unique, prefixed by suite), `input` (the raw text/reference), `expected` (ground truth output), `tags` (for filtering and analysis).

## Scoring

The `extraction_judge` produces a composite score from 0.0 to 1.0:

- **Header accuracy (weight 0.2):** Field-level match on supplier name, quote number, date, customer name. Uses token-overlap similarity with a 0.8 threshold.
- **Line item accuracy (weight 0.5):** Count match (0.3), description similarity (0.4), price accuracy (0.3). Descriptions matched via Jaccard similarity on lowercased tokens.
- **Totals accuracy (weight 0.3):** Per-field comparison of subtotal, tax, and total within percentage tolerance.

The `qualifier_judge` is a binary gate: PASS if composite score ≥ 0.75 and no critical failures (missing items, missing supplier name).

## Baseline Management

`eval/results/baseline.json` stores the current accuracy scores per suite. It is checked into git. The CI eval gate compares every PR's results against this baseline using thresholds from `policies/eval_gate_policy.json`:

- `classifier`: min 90% accuracy
- `line_items`: min 85% accuracy
- `recovery`: min 80% accuracy
- Regression tolerance: 2% (scores can drop by up to 2 percentage points without blocking)

To update the baseline after a verified improvement:

```bash
python eval/run_evals.py --update-baseline
```

## Adding New Test Cases

1. Create the labeled case in the appropriate `.jsonl` file
2. Run `python eval/run_evals.py --suite <suite>` to verify it passes
3. If the new case reveals a real issue, fix the pipeline first
4. Update baseline if accuracy improved: `--update-baseline`
5. Commit both the golden file and baseline together

## Labeling Tool

`scripts/label_pdfs.py` provides a CLI for creating golden labels from real supplier quotes. It extracts text, runs a candidate extraction, and prompts for corrections.
