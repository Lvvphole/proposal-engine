from __future__ import annotations

import json
from pathlib import Path

from skill_opt.models import SkillEdit


def record_rejected_edit(
    path: str,
    edits: list[SkillEdit],
    before_score: float,
    after_score: float,
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "before_score": before_score,
        "after_score": after_score,
        "score_delta": after_score - before_score,
        "edits": [e.model_dump(mode="json") for e in edits],
    }

    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def load_rejected_context(path: str, limit: int = 20) -> str:
    p = Path(path)
    if not p.exists():
        return ""

    rows = p.read_text(encoding="utf-8").splitlines()[-limit:]
    return "\n".join(rows)
