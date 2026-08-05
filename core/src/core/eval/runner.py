from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx
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
        if fraction < self._pass_rate:
            return "Response: issue resolved successfully."
        return "Response: I cannot help with that, please contact support."


class HttpAgentRunner:
    """Replay an eval case through a customer-owned HTTP agent endpoint.

    The endpoint receives ``{"trace": ..., "config": {"prompt": ..., "skills": [...]}}``
    and must return ``{"response": "..."}``. This keeps Anneal independent of
    the customer's agent runtime while preserving paired baseline/candidate evals.
    """

    def __init__(self, endpoint: str, *, api_key: str = "", timeout: float = 60.0) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout = timeout

    def run(self, trace: Trace, config: AgentConfig) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        response = httpx.post(
            self._endpoint,
            headers=headers,
            json={
                "trace": trace.model_dump(mode="json"),
                "config": {"prompt": config.prompt, "skills": list(config.skills)},
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        result = body.get("response") if isinstance(body, dict) else None
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Agent runner must return a non-empty 'response' string")
        return result
