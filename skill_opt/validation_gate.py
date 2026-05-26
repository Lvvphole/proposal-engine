from __future__ import annotations

_MIN_DELTA = 0.0


def held_out_gate(before: float, after: float) -> bool:
    return after >= before + _MIN_DELTA
