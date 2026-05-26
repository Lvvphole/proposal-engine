# /run-evals

Run evaluation suites and compare against the baseline.

## Usage

```
/run-evals                     # Run all suites
/run-evals classifier          # Run specific suite
/run-evals --update-baseline   # Update baseline after verified improvement
```

## Steps

1. Execute: `python eval/run_evals.py` (with optional `--suite` or `--update-baseline` flags).
2. Parse the output for pass/fail status per suite.
3. If any suite fails (regression detected):
   - Show the specific accuracy drop (current vs. baseline)
   - Identify which test cases failed
   - Suggest investigation steps:
     a. Check recent changes to agents/ or pipelines/
     b. Run the failing cases individually for detailed output
     c. Compare extraction output to golden expected output
4. If all suites pass:
   - Show accuracy per suite with delta from baseline
   - If accuracy improved, ask if the user wants to update the baseline
5. If `--update-baseline` was used:
   - Confirm the new baseline was written to `eval/results/baseline.json`
   - Remind the user to commit the updated baseline

## Thresholds (from policies/eval_gate_policy.json)

- Classifier: ≥ 90% accuracy
- Line Items: ≥ 85% accuracy
- Recovery: ≥ 80% accuracy
- Regression tolerance: 2%
