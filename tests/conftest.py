"""Test configuration — set environment defaults and clear caches."""

from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_proposals.db")

from core.config import get_config
get_config.cache_clear()
