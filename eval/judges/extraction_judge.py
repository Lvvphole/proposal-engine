from __future__ import annotations


def score_extraction(candidate: dict, expected: dict) -> float:
    """Return 1.0 if candidate output matches expected output, else 0.0."""
    return 1.0 if candidate.get("output") == expected.get("output") else 0.0
