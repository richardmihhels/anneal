from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from shared.models import Trace


@dataclass(frozen=True)
class AgentConfig:
    prompt: str
    skills: tuple[str, ...]


@runtime_checkable
class AgentRunner(Protocol):
    def run(self, trace: Trace, config: AgentConfig) -> str:
        """Run the agent on the given trace and return the agent's response text."""
        ...


class FakeAgentRunner:
    """Deterministic fake runner for tests and CLI demos.

    Produces a 'pass' response for the first `pass_rate` fraction of traces
    (by hash), simulating a consistent success rate.
    """

    def __init__(self, pass_rate: float = 0.5) -> None:
        if not 0.0 <= pass_rate <= 1.0:
            raise ValueError("pass_rate must be in [0, 1]")
        self._pass_rate = pass_rate

    def run(self, trace: Trace, config: AgentConfig) -> str:
        import hashlib

        h = int(hashlib.sha256(f"{config.prompt}:{trace.id}".encode()).hexdigest()[-8:], 16)
        fraction = h / 0xFFFFFFFF
        return "Response: issue resolved successfully." if fraction < self._pass_rate else "Response: I cannot help with that, please contact support."
