# SkillOpt

Bounded text-space optimizer for agent skills.

## Wired components

- optimizer model adapter: `skill_opt/optimizer_client.py`
- eval harness adapter: `skill_opt/eval_adapter.py`
- bounded edit loop: `skill_opt/optimizer.py`
- rejected-edit memory: `skill_opt/rejected_buffer.py`
- held-out validation gate: `skill_opt/validation_gate.py`
- best skill export: `skill_opt/export.py`

## Production rule

The optimizer model is offline training-time only. The deployed artifact is `best_skill.md`.
