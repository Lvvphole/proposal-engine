# Eval Framework

Automated evaluation of extraction accuracy against golden datasets.

## Structure

```
eval/
├── goldens/              # Ground-truth labeled datasets
│   ├── classifier_v1.jsonl
│   ├── line_items_v1.jsonl
│   └── recovery_v1.jsonl
├── judges/               # Scoring functions
│   ├── extraction_judge.py
│   └── qualifier_judge.py
├── results/
│   └── baseline.json     # Current baseline scores (checked into git)
└── run_evals.py          # CLI entry point
```

## Usage

```bash
# Run all evals and compare against baseline
python eval/run_evals.py

# Run specific eval suite
python eval/run_evals.py --suite classifier

# Update baseline after verified improvement
python eval/run_evals.py --update-baseline
```

## Golden Dataset Format

Each `.jsonl` file contains one test case per line:

```json
{"id": "cls-001", "input": "...", "expected": {...}, "tags": ["structured", "roofing"]}
```

## CI Integration

The `eval-gate.yml` workflow runs evals on every PR and blocks merge if accuracy regresses below baseline thresholds defined in `policies/eval_gate_policy.json`.
