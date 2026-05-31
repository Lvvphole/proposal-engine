"""Model capability registry — maps model IDs to their capability profiles."""

from __future__ import annotations

from dataclasses import dataclass

from contracts.errors import PolicyViolationError


@dataclass(frozen=True)
class ModelCapabilities:
    model_id: str
    context_window: int
    supports_vision: bool
    supports_tools: bool
    input_cost_per_million: float
    output_cost_per_million: float


_REGISTRY: dict[str, ModelCapabilities] = {
    "claude-sonnet-4-20250514": ModelCapabilities(
        model_id="claude-sonnet-4-20250514",
        context_window=200_000,
        supports_vision=True,
        supports_tools=True,
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
    ),
    "claude-haiku-3-5-20241022": ModelCapabilities(
        model_id="claude-haiku-3-5-20241022",
        context_window=200_000,
        supports_vision=True,
        supports_tools=True,
        input_cost_per_million=0.8,
        output_cost_per_million=4.0,
    ),
    "claude-haiku-4-5-20251001": ModelCapabilities(
        model_id="claude-haiku-4-5-20251001",
        context_window=200_000,
        supports_vision=True,
        supports_tools=True,
        input_cost_per_million=0.8,
        output_cost_per_million=4.0,
    ),
}


def get_capabilities(model_id: str) -> ModelCapabilities:
    """Return the capability profile for a model, raising KeyError if unknown."""
    if model_id not in _REGISTRY:
        raise KeyError(f"Unknown model: {model_id!r}. Register it with register_model().")
    return _REGISTRY[model_id]


def register_model(model_id: str, caps: ModelCapabilities) -> None:
    """Add or replace a model entry in the registry."""
    _REGISTRY[model_id] = caps


def assert_capability(model_id: str, capability: str) -> None:
    """Raise PolicyViolationError if the model lacks the named capability.

    Supported capability names: 'vision', 'tools'.
    """
    caps = get_capabilities(model_id)
    capability_map = {
        "vision": caps.supports_vision,
        "tools": caps.supports_tools,
    }
    if capability not in capability_map:
        raise ValueError(f"Unknown capability: {capability!r}")
    if not capability_map[capability]:
        raise PolicyViolationError(
            f"Model {model_id!r} does not support capability {capability!r}",
            context={"model_id": model_id, "capability": capability},
        )
