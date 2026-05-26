from __future__ import annotations

from skill_opt.models import Trajectory


def mean_score(trajectories: list[Trajectory]) -> float:
    if not trajectories:
        return 0.0
    return sum(t.score for t in trajectories) / len(trajectories)
