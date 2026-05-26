from __future__ import annotations

from pathlib import Path


def export_best_skill(skill: str, path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(skill, encoding="utf-8")
    return str(p)
