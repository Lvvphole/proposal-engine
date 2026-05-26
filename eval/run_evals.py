"""Eval runner — CLI entry point for evaluation suites.

Loads golden datasets, runs them through the relevant pipeline
components, scores with judges, and compares against the baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).parent
GOLDENS_DIR = EVAL_DIR / "goldens"
RESULTS_DIR = EVAL_DIR / "results"
BASELINE_PATH = RESULTS_DIR / "baseline.json"


def load_goldens(suite: str) -> list[dict]:
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


def load_baseline() -> dict:
    """Load the current baseline scores."""
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text())
    return {}


def save_baseline(results: dict) -> None:
    """Update the baseline file."""
    BASELINE_PATH.write_text(json.dumps(results, indent=2) + "\n")


def run_suite(suite: str) -> dict:
    """Run a single eval suite and return scores.

    Returns:
        Dict with keys: suite, total, passed, failed, accuracy, details.
    """
    cases = load_goldens(suite)
    if not cases:
        return {"suite": suite, "total": 0, "passed": 0, "failed": 0, "accuracy": 0.0}

    passed = 0
    failed = 0
    details = []

    for case in cases:
        # Placeholder: in production, each case is run through the
        # actual pipeline and scored by the appropriate judge
        case_id = case.get("id", "unknown")
        # Stub: mark all as passed for initial scaffold
        passed += 1
        details.append({"id": case_id, "status": "passed", "score": 1.0})

    total = passed + failed
    accuracy = passed / total if total > 0 else 0.0

    return {
        "suite": suite,
        "total": total,
        "passed": passed,
        "failed": failed,
        "accuracy": round(accuracy, 4),
        "details": details,
    }


def compare_to_baseline(results: dict, baseline: dict) -> bool:
    """Check if results meet or exceed baseline thresholds.

    Returns True if all suites pass.
    """
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
    parser.add_argument("--update-baseline", action="store_true", help="Update baseline with current results")
    args = parser.parse_args()

    suites = [args.suite] if args.suite else ["classifier", "line_items", "recovery"]

    print("=" * 60)
    print("Proposal Engine — Eval Runner")
    print("=" * 60)

    results = {}
    for suite in suites:
        print(f"\nRunning: {suite}")
        result = run_suite(suite)
        results[suite] = result
        print(f"  {result['passed']}/{result['total']} passed ({result['accuracy']:.2%})")

    # Compare to baseline
    baseline = load_baseline()
    if baseline:
        print("\n--- Baseline Comparison ---")
        passed = compare_to_baseline(results, baseline)
    else:
        print("\nNo baseline found. Run with --update-baseline to set one.")
        passed = True

    if args.update_baseline:
        save_baseline(results)
        print("\nBaseline updated.")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
