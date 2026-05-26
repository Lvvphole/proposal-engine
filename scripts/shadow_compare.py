"""Shadow comparison tool.

Runs a document through all three extraction pipelines (A, B, C)
simultaneously and compares results. Used to determine the optimal
pipeline for a new supplier or to validate pipeline changes.

Usage:
    python scripts/shadow_compare.py <document_text_file>
    python scripts/shadow_compare.py --stdin < quote.txt
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


async def run_pipeline_stub(pipeline: str, text: str) -> dict:
    """Stub: run a pipeline and return results.

    In production, this imports and calls the actual pipeline run functions.
    For now, returns placeholder results for development.
    """
    # TODO: Import actual pipeline runners
    # from pipelines.pipeline_a.run import run as run_a
    # from pipelines.pipeline_b.run import run as run_b
    # from pipelines.pipeline_c.run import run as run_c

    return {
        "pipeline": pipeline,
        "status": "stub",
        "line_item_count": 0,
        "confidence": 0.0,
        "cost_usd": 0.0,
        "message": f"Pipeline {pipeline} stub — connect to actual pipeline for real results",
    }


async def shadow_compare(text: str) -> dict:
    """Run all three pipelines and compare results."""
    results = await asyncio.gather(
        run_pipeline_stub("a", text),
        run_pipeline_stub("b", text),
        run_pipeline_stub("c", text),
    )

    pipeline_results = {r["pipeline"]: r for r in results}

    # Determine best pipeline by confidence (when connected to real pipelines)
    best = max(results, key=lambda r: r.get("confidence", 0))

    return {
        "pipelines": pipeline_results,
        "recommended": best["pipeline"],
        "recommended_confidence": best.get("confidence", 0),
    }


def format_comparison(comparison: dict) -> str:
    """Format comparison results for display."""
    lines = [
        "Shadow Comparison Results",
        "=" * 50,
    ]

    for name in ["a", "b", "c"]:
        result = comparison["pipelines"].get(name, {})
        lines.append(f"\nPipeline {name.upper()}:")
        lines.append(f"  Status:     {result.get('status', 'unknown')}")
        lines.append(f"  Items:      {result.get('line_item_count', '?')}")
        lines.append(f"  Confidence: {result.get('confidence', 0):.2%}")
        lines.append(f"  Cost:       ${result.get('cost_usd', 0):.4f}")

    lines.append(f"\nRecommended: Pipeline {comparison['recommended'].upper()}")
    lines.append(f"Confidence:  {comparison['recommended_confidence']:.2%}")

    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow compare all extraction pipelines")
    parser.add_argument("file", type=Path, nargs="?", help="Document text file")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    elif args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}")
            return 1
        text = args.file.read_text()
    else:
        parser.print_help()
        return 1

    if not text.strip():
        print("Empty input.")
        return 1

    comparison = await shadow_compare(text)

    if args.json:
        print(json.dumps(comparison, indent=2))
    else:
        print(format_comparison(comparison))

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
