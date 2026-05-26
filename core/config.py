"""Centralized configuration.

All config flows through here.  Environment variables → typed Config object.
No module should read os.environ directly.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration, loaded from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ── API Keys ─────────────────────────────────────────────────────
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = Field(
        "sqlite:///./proposal_engine.db", alias="DATABASE_URL"
    )

    # ── LLM Defaults ────────────────────────────────────────────────
    default_model: str = Field("claude-sonnet-4-20250514", alias="DEFAULT_MODEL")
    classifier_model: str = Field("claude-haiku-3-5-20241022", alias="CLASSIFIER_MODEL")
    extraction_model: str = Field("claude-sonnet-4-20250514", alias="EXTRACTION_MODEL")
    max_tokens: int = Field(4096, alias="MAX_TOKENS")

    # ── Budget ───────────────────────────────────────────────────────
    budget_daily_limit_usd: Decimal = Field(
        Decimal("25.00"), alias="BUDGET_DAILY_LIMIT_USD"
    )
    budget_per_envelope_limit_usd: Decimal = Field(
        Decimal("2.00"), alias="BUDGET_PER_ENVELOPE_LIMIT_USD"
    )

    # ── Server ───────────────────────────────────────────────────────
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")
    debug: bool = Field(False, alias="DEBUG")

    # ── MCP ──────────────────────────────────────────────────────────
    mcp_server_port: int = Field(3100, alias="MCP_SERVER_PORT")


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Singleton config accessor."""
    return Config()  # type: ignore[call-arg]
