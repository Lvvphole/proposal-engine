from __future__ import annotations

from collections.abc import Callable

from eval.judges.extraction_judge import score_extraction
from skill_opt.models import Trajectory

Runner = Callable[[dict, str], tuple[str, str]]


def eval_split(tasks: list[dict], skill: str, runner: Runner) -> list[Trajectory]:
    trajectories: list[Trajectory] = []

    for task in tasks:
        output, trace = runner(task, skill)

        expected = task.get("expected", {})
        candidate = task.get("candidate", {"output": output})
        score = score_extraction(candidate, expected)

        trajectories.append(
            Trajectory(
                task_id=str(task.get("id", "")),
                input_text=str(task.get("input", "")),
                output_text=output,
                score=float(score),
                trace=trace,
            )
        )

    return trajectories
