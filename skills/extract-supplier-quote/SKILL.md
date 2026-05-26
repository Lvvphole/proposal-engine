# Skill: Extract Supplier Quote

## Purpose

Run the full extraction pipeline on a supplier quote document. Produces a validated `ExtractionResult` and routes to human review.

## Trigger

User provides a supplier quote (PDF, image, or pasted text) and asks to extract it.

## Workflow

1. **Receive document.** Accept the file path or pasted content. If a file, read it from disk.

2. **Check budget.** Call `harness/budget.py` to verify both per-envelope and daily limits have headroom. If either is exhausted, inform the user and stop.

3. **Classify.** Run the document through the classifier agent (`agents/classifier/AGENT.md`). Log the detected format, assigned pipeline, and confidence score.

4. **Extract.** Dispatch to the assigned pipeline:
   - Pipeline A (`pipelines/pipeline_a/run.py`): header → line items → totals, with handoff validation between each step
   - Pipeline B (`pipelines/pipeline_b/run.py`): single-pass semi-structured extraction
   - Pipeline C (`pipelines/pipeline_c/run.py`): single-pass unstructured fallback

5. **Validate.** Run the extraction through `pipelines/validation_gate.py`. The gate checks: items exist, required fields present, subtotal consistency (2% tolerance), no negative prices, confidence threshold met.

6. **Handle failures.** If validation fails:
   - Route to recovery agent (`agents/recovery_agent/AGENT.md`) for up to 2 retry attempts
   - If recovery exhausts, escalate to human review with the best extraction so far

7. **Present results.** Display the extraction to the user in a readable format: header fields, line item table, totals, quality score, and confidence.

## Output

- `ExtractionResult` object (JSON)
- Audit log entry in `harness/audit.py`
- Budget usage update

## Contracts

- Input: raw document (text, PDF bytes, or image)
- Output: `contracts/extraction.py::ExtractionResult`
- Errors: `BudgetExceededError`, `ContractViolation`, `RecoveryExhaustedError`

## Example

```
User: Extract this quote from ABC Supply [attaches PDF]
Claude: Classifying... detected structured_table format (confidence: 0.92), routing to Pipeline A.
        Extracting header... ✓ ABC Supply, Quote #Q-2024-1234
        Extracting line items... ✓ 5 items found
        Extracting totals... ✓ Subtotal $5,102.50, Tax $357.18, Total $5,459.68
        Validation... ✓ PASSED (quality score: 0.94)
        Cost: $0.07 (1,847 input + 523 output tokens)
```
