from skill_opt.models import EditType, SkillEdit
from skill_opt.optimizer import optimize_skill


class FakeOptimizer:
    def propose_edits(self, prompt: str):
        return [
            SkillEdit(
                edit_type=EditType.ADD,
                target="<!-- SKILLOPT_FAST_RULES -->",
                content="- Always verify extracted totals against line item sums.",
                rationale="Adds reusable verification procedure.",
            )
        ]


def runner(task: dict, skill: str):
    return task.get("expected_output", "ok"), "trace"


def test_optimizer_model_and_eval_harness_wire(tmp_path):
    result = optimize_skill(
        initial_skill="# Skill",
        train_tasks=[
            {
                "id": "train-1",
                "input": "quote",
                "expected_output": "ok",
                "candidate": {"output": "ok"},
                "expected": {"output": "ok"},
            }
        ],
        selection_tasks=[
            {
                "id": "sel-1",
                "input": "quote",
                "expected_output": "ok",
                "candidate": {"output": "ok"},
                "expected": {"output": "ok"},
            }
        ],
        runner=runner,
        optimizer_model=FakeOptimizer(),
        best_skill_path=str(tmp_path / "best_skill.md"),
        rejected_buffer_path=str(tmp_path / "rejected.jsonl"),
    )

    assert result.best_skill_path.endswith("best_skill.md")
