from __future__ import annotations

import json
from typing import Protocol

from core.llm import get_llm_config
from skill_opt.models import SkillEdit


class OptimizerModel(Protocol):
    def propose_edits(self, prompt: str) -> list[SkillEdit]: ...


class JsonOptimizerModel:
    """Production adapter for optimizer-model reflection.

    Replace `_call_model` with LiteLLM/OpenAI/Anthropic call in core.llm.
    """

    def propose_edits(self, prompt: str) -> list[SkillEdit]:
        raw = self._call_model(prompt)
        data = json.loads(raw)
        return [SkillEdit(**item) for item in data.get("edits", [])]

    def _call_model(self, prompt: str) -> str:
        cfg = get_llm_config()
        # Intentional boundary:
        # actual provider call should live in core.llm, not inside SkillOpt.
        # This keeps routing, temperature, telemetry, and budgets centralized.
        raise NotImplementedError(
            f"Wire provider call in core.llm using config={cfg}. Prompt length={len(prompt)}"
        )
