from __future__ import annotations

import json

from skill_opt.models import SkillEdit, Trajectory
from skill_opt.optimizer_client import OptimizerModel


def build_reflection_prompt(
    current_skill: str,
    trajectories: list[Trajectory],
    rejected_context: str = "",
) -> str:
    payload = {
        "objective": "Improve one agent skill document using bounded add/delete/replace edits.",
        "rules": [
            "Return JSON only.",
            "Use only add, delete, replace edits.",
            "Do not edit protected slow-update region.",
            "Prefer reusable procedural rules over instance-specific fixes.",
            "Use strict minimal edits.",
        ],
        "current_skill": current_skill,
        "trajectories": [t.model_dump() for t in trajectories],
        "rejected_context": rejected_context,
        "output_schema": {
            "edits": [
                {
                    "edit_type": "add|delete|replace",
                    "target": "exact text anchor",
                    "content": "replacement or inserted text",
                    "rationale": "why this improves held-out score",
                }
            ]
        },
    }
    return json.dumps(payload)


def reflect_to_edits(
    current_skill: str,
    trajectories: list[Trajectory],
    optimizer_model: OptimizerModel,
    rejected_context: str = "",
) -> list[SkillEdit]:
    prompt = build_reflection_prompt(current_skill, trajectories, rejected_context)
    return optimizer_model.propose_edits(prompt)
