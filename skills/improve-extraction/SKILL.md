# Skill: Improve Extraction

## Purpose

Diagnose extraction accuracy issues and implement targeted improvements. Used after a human reviewer identifies errors in an extraction.

## Trigger

User reports that an extraction had errors (wrong prices, missing items, incorrect supplier name, etc.) or asks to improve accuracy for a specific supplier.

## Workflow

1. **Identify the issue.** Gather:
   - Envelope ID of the failed extraction
   - What was wrong (specific fields, missing items, incorrect values)
   - The correct values (human-provided ground truth)

2. **Analyze root cause.** Check:
   - Was the document classified correctly? (wrong pipeline)
   - Was the format unusual? (merged cells, handwritten, multi-page)
   - Was the confidence score already low? (system knew it was uncertain)
   - Is this a known supplier with a preferred pipeline?

3. **Create golden test case.** Write a new entry in the appropriate `.jsonl` golden file with:
   - The input document text
   - The correct expected output
   - Tags for categorization

4. **Update supplier catalog.** If this is a supplier-specific issue:
   - Register or update the supplier in `rag/supplier_catalog.py`
   - Set the correct preferred pipeline
   - Add field mapping hints if the format is non-standard

5. **Add few-shot example.** If the error was in extraction quality (not routing):
   - Add the correct extraction as a few-shot example in `rag/few_shot_selector.py`
   - This will be automatically selected for similar documents in the future

6. **Store human correction.** Record the correction in `memory/learned_store.py` so the system learns from this specific error pattern.

7. **Run evals.** Execute `python eval/run_evals.py` to verify the fix doesn't regress other test cases.

8. **Report.** Summarize what was changed and the impact on eval scores.

## Output

- Updated golden dataset
- Updated supplier catalog (if applicable)
- New few-shot example (if applicable)
- Eval results showing no regression
