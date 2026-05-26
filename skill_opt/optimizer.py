from __future__ import annotations

from skill_opt.edit_budget import clip_edits
from skill_opt.edits import apply_edits, ensure_skill_regions
from skill_opt.eval_adapter import Runner, eval_split
from skill_opt.export import export_best_skill
from skill_opt.models import OptimizationResult
from skill_opt.optimizer_client import OptimizerModel
from skill_opt.reflection import reflect_to_edits
from skill_opt.rejected_buffer import load_rejected_context, record_rejected_edit
from skill_opt.scoring import mean_score
from skill_opt.validation_gate import held_out_gate


def optimize_skill(
    initial_skill: str,
    train_tasks: list[dict],
    selection_tasks: list[dict],
    runner: Runner,
    optimizer_model: OptimizerModel,
    edit_budget: int = 4,
    rejected_buffer_path: str = "skill_opt/artifacts/rejected_edits.jsonl",
    best_skill_path: str = "skill_opt/artifacts/best_skill.md",
) -> OptimizationResult:
    current_skill = ensure_skill_regions(initial_skill)

    before_selection = eval_split(selection_tasks, current_skill, runner)
    before_score = mean_score(before_selection)

    train_rollouts = eval_split(train_tasks, current_skill, runner)
    rejected_context = load_rejected_context(rejected_buffer_path)

    proposed_edits = reflect_to_edits(
        current_skill=current_skill,
        trajectories=train_rollouts,
        optimizer_model=optimizer_model,
        rejected_context=rejected_context,
    )

    bounded_edits = clip_edits(proposed_edits, edit_budget)

    if not bounded_edits:
        path = export_best_skill(current_skill, best_skill_path)
        return OptimizationResult(
            accepted=False,
            before_score=before_score,
            after_score=before_score,
            best_skill_path=path,
            rejected_count=0,
        )

    candidate_skill = apply_edits(current_skill, bounded_edits)
    after_selection = eval_split(selection_tasks, candidate_skill, runner)
    after_score = mean_score(after_selection)

    if held_out_gate(before_score, after_score):
        path = export_best_skill(candidate_skill, best_skill_path)
        return OptimizationResult(
            accepted=True,
            before_score=before_score,
            after_score=after_score,
            best_skill_path=path,
            rejected_count=0,
        )

    record_rejected_edit(
        path=rejected_buffer_path,
        edits=bounded_edits,
        before_score=before_score,
        after_score=after_score,
    )

    path = export_best_skill(current_skill, best_skill_path)
    return OptimizationResult(
        accepted=False,
        before_score=before_score,
        after_score=after_score,
        best_skill_path=path,
        rejected_count=len(bounded_edits),
    )
