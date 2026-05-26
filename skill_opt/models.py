from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class EditType(str, Enum):
    ADD = "add"
    DELETE = "delete"
    REPLACE = "replace"


class SkillEdit(BaseModel):
    edit_type: EditType
    target: str
    content: str = ""
    rationale: str = ""


class Trajectory(BaseModel):
    task_id: str
    input_text: str
    output_text: str
    score: float
    trace: str = ""


class OptimizationResult(BaseModel):
    accepted: bool
    before_score: float
    after_score: float
    best_skill_path: str
    rejected_count: int
