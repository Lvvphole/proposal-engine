from __future__ import annotations

from skill_opt.models import EditType, SkillEdit

_FAST_REGION = "<!-- SKILLOPT_FAST_RULES -->"
_SLOW_REGION = "<!-- SKILLOPT_SLOW_UPDATE -->"


def ensure_skill_regions(skill: str) -> str:
    if _FAST_REGION not in skill:
        skill = skill + f"\n\n{_FAST_REGION}\n"
    return skill


def apply_edits(skill: str, edits: list[SkillEdit]) -> str:
    for edit in edits:
        if edit.edit_type == EditType.ADD:
            skill = skill.replace(edit.target, edit.target + "\n" + edit.content, 1)
        elif edit.edit_type == EditType.DELETE:
            skill = skill.replace(edit.target, "", 1)
        elif edit.edit_type == EditType.REPLACE:
            skill = skill.replace(edit.target, edit.content, 1)
    return skill
