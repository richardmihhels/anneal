from __future__ import annotations

from typing import Any

import httpx
import pytest
from core.eval.runner import AgentConfig, HttpAgentRunner
from core.testing.generator import generate_trace


def test_http_agent_runner_sends_trace_and_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={"response": "resolved"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    runner = HttpAgentRunner("https://agent.example/eval", api_key="runner-secret")
    response = runner.run(
        generate_trace("wrong_tool", seed=1),
        AgentConfig(prompt="candidate prompt", skills=("lookup",)),
    )

    assert response == "resolved"
    assert captured["url"] == "https://agent.example/eval"
    assert captured["headers"] == {"Authorization": "Bearer runner-secret"}
    assert captured["json"]["config"] == {
        "prompt": "candidate prompt",
        "skills": ["lookup"],
    }


def test_http_agent_runner_rejects_invalid_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, *args, **kwargs: httpx.Response(
            200,
            json={},
            request=httpx.Request("POST", url),
        ),
    )
    runner = HttpAgentRunner("https://agent.example/eval")
    with pytest.raises(ValueError, match="response"):
        runner.run(generate_trace("wrong_tool", seed=2), AgentConfig(prompt="candidate", skills=()))
