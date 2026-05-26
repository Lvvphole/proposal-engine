from __future__ import annotations

import os


def get_llm_config() -> dict:
    return {
        "model": os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.0")),
    }
