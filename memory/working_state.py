"""Working state — request-scoped memory for active processing.

Holds the current envelope and intermediate agent outputs during
a single processing run.  Cleared when processing completes.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from contracts.envelope import Envelope

_current_envelope: ContextVar[Envelope | None] = ContextVar("current_envelope", default=None)
_agent_outputs: ContextVar[dict[str, Any]] = ContextVar("agent_outputs", default={})


def set_envelope(envelope: Envelope) -> None:
    _current_envelope.set(envelope)


def get_envelope() -> Envelope | None:
    return _current_envelope.get()


def store_agent_output(agent_name: str, output: Any) -> None:
    outputs = _agent_outputs.get()
    outputs[agent_name] = output
    _agent_outputs.set(outputs)


def get_agent_output(agent_name: str) -> Any | None:
    return _agent_outputs.get().get(agent_name)


def clear() -> None:
    _current_envelope.set(None)
    _agent_outputs.set({})
