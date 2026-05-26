# /review-contract-change

Review a proposed change to the contracts layer for safety and backward compatibility.

## Usage

```
/review-contract-change
```

Run this command before merging any PR that modifies files in `contracts/`.

## Steps

1. Identify changed files in `contracts/` (diff against main branch).
2. For each changed contract:
   - Check if any fields were removed or renamed (breaking change)
   - Check if any validators were loosened (could allow invalid data)
   - Check if any validators were tightened (could reject previously valid data)
   - Verify `__init__.py` exports are still complete
3. Run contract tests: `pytest tests/test_contracts.py -v`
4. Run validation gate tests: `pytest tests/test_validation_gate.py -v`
5. Check downstream impact:
   - Search for all imports of changed contracts across the codebase
   - Verify each usage site is compatible with the changes
6. If breaking changes are found:
   - List all affected files
   - Suggest a migration path
   - Flag whether this requires a version bump
7. Generate a summary: safe changes, breaking changes, migration needed (yes/no), test results.

## Output

Contract change review report with pass/fail determination.
