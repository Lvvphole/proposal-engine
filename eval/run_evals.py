"""Eval runner — CLI entry point for evaluation suites.

Loads golden datasets, runs each case's recorded model output through the
relevant **deterministic** pipeline component, scores it with the appropriate
judge, and compares against the baseline. No live LLM calls — the suites guard
the post-processing logic we own (JSON recovery, line-item validation,
classification routing, pricing, failure detection), so the gate is stable and
reproducible in CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).parent
GOLDENS_DIR = EVAL_DIR / "goldens"
RESULTS_DIR = EVAL_DIR / "results"
BASELINE_PATH = RESULTS_DIR / "baseline.json"

# A scorer takes a golden case and returns (passed, score in [0, 1]).
Scorer = Callable[[dict[str, Any]], "tuple[bool, float]"]


def load_goldens(suite: str) -> list[dict[str, Any]]:
    """Load a golden dataset by suite name."""
    path = GOLDENS_DIR / f"{suite}_v1.jsonl"
    if not path.exists():
        print(f"Golden dataset not found: {path}")
        return []
    cases = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_baseline() -> dict[str, Any]:
    """Load the current baseline scores."""
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text())
    return {}


def save_baseline(results: dict[str, Any]) -> None:
    """Update the baseline file."""
    BASELINE_PATH.write_text(json.dumps(results, indent=2) + "\n")


# ── Scorers ──────────────────────────────────────────────────────────────


def _score_classifier(case: dict[str, Any]) -> tuple[bool, float]:
    """Parse the model's classification and apply routing; exact-match the result."""
    from contracts.classifier import ClassificationResult
    from pipelines.parsing import extract_json

    result = ClassificationResult.model_validate(extract_json(case["model_response"]))
    pipeline = "c" if result.needs_fallback else result.pipeline
    expected = case["expected"]
    ok = pipeline == expected["pipeline"] and result.format.value == expected["format"]
    return ok, 1.0 if ok else 0.0


def _score_line_items(case: dict[str, Any]) -> tuple[bool, float]:
    """Recover JSON, validate line items row-by-row, and judge against ground truth."""
    from eval.judges.extraction_judge import score_line_items
    from pipelines.parsing import extract_json, parse_line_items

    items = parse_line_items(extract_json(case["model_response"]))
    extracted = [item.model_dump(mode="json") for item in items]
    score = score_line_items(extracted, case["expected"]["line_items"])
    return score >= 0.85, round(score, 4)


def _score_recovery(case: dict[str, Any]) -> tuple[bool, float]:
    """Verify the documented extraction failure is deterministically detectable."""
    error = case["error"]
    if error == "line_item_count_mismatch":
        got = len(case["failed_extraction"].get("line_items", []))
        detected = got != case["expected_count"]
    elif error == "subtotal_mismatch":
        stated = Decimal(str(case["failed_extraction"]["totals"]["subtotal"]))
        computed = Decimal(str(case["computed_subtotal"]))
        tolerance = max(stated * Decimal("0.02"), Decimal("1.00"))
        detected = abs(computed - stated) > tolerance
    else:
        detected = False
    return detected, 1.0 if detected else 0.0


def _score_pricing(case: dict[str, Any]) -> tuple[bool, float]:
    """Build the proposal and exact-match the priced totals (money must be exact)."""
    from contracts.contractor import ContractorProfile
    from contracts.extraction import ExtractionResult
    from pipelines.proposal_builder import build_proposal

    extraction = ExtractionResult.model_validate(case["extraction"])
    contractor = ContractorProfile.model_validate(case["contractor"])
    proposal = build_proposal(extraction, contractor)

    expected = case["expected"]
    ok = all(
        getattr(proposal, field) == Decimal(str(expected[field]))
        for field in ("subtotal", "markup_amount", "tax_amount", "total")
    )
    return ok, 1.0 if ok else 0.0


SCORERS: dict[str, Scorer] = {
    "classifier": _score_classifier,
    "line_items": _score_line_items,
    "recovery": _score_recovery,
    "pricing": _score_pricing,
}

DEFAULT_SUITES = ["classifier", "line_items", "recovery", "pricing"]


def run_suite(suite: str) -> dict[str, Any]:
    """Run a single eval suite and return scores."""
    cases = load_goldens(suite)
    scorer = SCORERS.get(suite)
    if not cases or scorer is None:
        return {"suite": suite, "total": 0, "passed": 0, "failed": 0, "accuracy": 0.0}

    passed = 0
    details = []
    for case in cases:
        case_id = case.get("id", "unknown")
        try:
            ok, score = scorer(case)
        except Exception as exc:  # a scorer error is a failed case, not a crash
            ok, score = False, 0.0
            details.append({"id": case_id, "status": "error", "score": 0.0, "error": str(exc)})
            continue
        passed += int(ok)
        details.append({"id": case_id, "status": "passed" if ok else "failed", "score": score})

    total = len(cases)
    return {
        "suite": suite,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "details": details,
    }


def compare_to_baseline(results: dict[str, Any], baseline: dict[str, Any]) -> bool:
    """Check if results meet or exceed baseline accuracy. Returns True if all pass."""
    all_pass = True
    for suite_name, suite_result in results.items():
        baseline_accuracy = baseline.get(suite_name, {}).get("accuracy", 0.0)
        current_accuracy = suite_result.get("accuracy", 0.0)

        if current_accuracy < baseline_accuracy:
            print(f"  REGRESSION: {suite_name} — {current_accuracy:.2%} < {baseline_accuracy:.2%}")
            all_pass = False
        else:
            delta = current_accuracy - baseline_accuracy
            print(f"  OK: {suite_name} — {current_accuracy:.2%} (Δ +{delta:.2%})")

    return all_pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run proposal-engine eval suites")
    parser.add_argument("--suite", type=str, default=None, help="Run specific suite only")
    parser.add_argument(
        "--update-baseline", action="store_true", help="Update baseline with current results"
    )
    args = parser.parse_args()

    suites = [args.suite] if args.suite else DEFAULT_SUITES

    print("=" * 60)
    print("Proposal Engine — Eval Runner")
    print("=" * 60)

    results = {}
    for suite in suites:
        print(f"\nRunning: {suite}")
        result = run_suite(suite)
        results[suite] = result
        print(f"  {result['passed']}/{result['total']} passed ({result['accuracy']:.2%})")

    baseline = load_baseline()
    if baseline:
        print("\n--- Baseline Comparison ---")
        passed = compare_to_baseline(results, baseline)
    else:
        print("\nNo baseline found. Run with --update-baseline to set one.")
        passed = True

    if args.update_baseline:
        # Strip per-case details from the persisted baseline for a clean diff.
        save_baseline(
            {k: {kk: vv for kk, vv in v.items() if kk != "details"} for k, v in results.items()}
        )
        print("\nBaseline updated.")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
