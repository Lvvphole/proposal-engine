from __future__ import annotations

from skill_opt.models import SkillEdit


def clip_edits(edits: list[SkillEdit], budget: int) -> list[SkillEdit]:
    return edits[:budget]
