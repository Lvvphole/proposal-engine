# /new-supplier-pipeline

Register a new supplier and configure optimal extraction for their quote format.

## Usage

```
/new-supplier-pipeline <supplier_name>
```

## Steps

1. Ask the user for a sample quote from this supplier (PDF, image, or text).
2. Run the classifier on the sample to detect the format.
3. Run all three pipelines (A, B, C) on the sample using `scripts/shadow_compare.py` logic.
4. Compare extraction quality across pipelines using `eval/judges/extraction_judge.py`.
5. Register the supplier in `rag/supplier_catalog.py` with the best-performing pipeline.
6. If extraction quality is below 0.8 on the best pipeline:
   - Examine the document structure for unusual formatting
   - Add field mapping hints to the supplier catalog entry
   - Create a few-shot example from the corrected extraction
7. Create a golden test case in the appropriate `.jsonl` file.
8. Run evals to verify no regression: `python eval/run_evals.py`.
9. Report: supplier name, selected pipeline, accuracy score, any special handling needed.

## Output

- Supplier registered in catalog with preferred pipeline
- Golden test case added
- Eval results confirming no regression
