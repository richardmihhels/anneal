"""SDK unit tests — scrubbing and callback handler (no HTTP calls)."""

from __future__ import annotations

import uuid

from anneal_sdk import AnnealClient
from anneal_sdk.handler import AnnealCallbackHandler
from anneal_sdk.scrub import scrub

# ── scrub ─────────────────────────────────────────────────────────────────────


def test_scrub_openai_key() -> None:
    data = {"openai_api_key": "sk-abcdefghijklmnopqrstuvwxyz012345"}
    result = scrub(data)
    assert result["openai_api_key"] == "[REDACTED]"


def test_scrub_anthropic_key_in_string() -> None:
    data = {"content": "key is sk-ant-api03-supersecretkey1234567890abcdef here"}
    result = scrub(data)
    assert "sk-ant" not in result["content"]


def test_scrub_bearer_in_string() -> None:
    data = {"header": "Bearer eyJhbGciOiJSUzI1NiJ9.verylongtoken9999999999"}
    result = scrub(data)
    assert "[REDACTED]" in result["header"]


def test_scrub_preserves_safe_data() -> None:
    data = {"model": "claude-3-5-sonnet", "temperature": 0.5, "max_tokens": 1024}
    assert scrub(data) == data


def test_scrub_nested() -> None:
    data = {"run": {"extra": {"api_key": "sk-mykey12345678901234567890abcdef"}}}
    result = scrub(data)
    assert result["run"]["extra"]["api_key"] == "[REDACTED]"


def test_scrub_list() -> None:
    data = [{"secret_key": "value123456"}, {"name": "ok"}]
    result = scrub(data)
    assert result[0]["secret_key"] == "[REDACTED]"
    assert result[1]["name"] == "ok"


# ── client ───────────────────────────────────────────────────────────────────


def test_client_from_env_adds_org_header(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ANNEAL_ENDPOINT", "http://anneal.test")
    monkeypatch.setenv("ANNEAL_API_KEY", "ann_test")
    monkeypatch.setenv("ANNEAL_ORG_ID", "org_test")

    client = AnnealClient.from_env()
    try:
        assert client._endpoint == "http://anneal.test"  # noqa: SLF001
        assert client._headers["Authorization"] == "Bearer ann_test"  # noqa: SLF001
        assert client._headers["X-Anneal-Org"] == "org_test"  # noqa: SLF001
    finally:
        client.close()


def test_client_prepare_run_scopes_metadata() -> None:
    client = AnnealClient("http://anneal.test", organization_id="org_test")
    try:
        prepared = client._prepare_run({"id": "run-1", "extra": {"metadata": {}}})  # noqa: SLF001
    finally:
        client.close()

    assert prepared["extra"]["metadata"]["organization_id"] == "org_test"


# ── callback handler ──────────────────────────────────────────────────────────


class _FakeClient:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send_langsmith_run(self, run: dict) -> None:
        self.sent.append(run)


def test_handler_flushes_on_chain_end() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")  # type: ignore[arg-type]
    run_id = uuid.uuid4()

    handler.on_chain_start(
        {"name": "support_chain"},
        {"messages": []},
        run_id=run_id,
    )
    handler.on_chain_end({"content": "done"}, run_id=run_id)

    assert len(fake.sent) == 1
    run = fake.sent[0]
    assert run["name"] == "support_chain"
    assert "agent_id:test-agent" in run["tags"]


def test_handler_child_runs_nested() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")  # type: ignore[arg-type]
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()

    handler.on_chain_start({"name": "parent"}, {}, run_id=parent_id)
    handler.on_tool_start({"name": "search_kb"}, "query", run_id=child_id, parent_run_id=parent_id)
    handler.on_tool_end("results", run_id=child_id)
    handler.on_chain_end({"output": "ok"}, run_id=parent_id)

    assert len(fake.sent) == 1
    run = fake.sent[0]
    assert len(run["child_runs"]) == 1
    assert run["child_runs"][0]["name"] == "search_kb"


def test_handler_does_not_flush_on_child_end() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")  # type: ignore[arg-type]
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()

    handler.on_chain_start({"name": "parent"}, {}, run_id=parent_id)
    handler.on_tool_start({"name": "tool"}, "x", run_id=child_id, parent_run_id=parent_id)
    handler.on_tool_end("y", run_id=child_id)

    # Parent not ended yet — nothing sent
    assert len(fake.sent) == 0


def test_handler_error_still_flushes() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")  # type: ignore[arg-type]
    run_id = uuid.uuid4()

    handler.on_chain_start({"name": "chain"}, {}, run_id=run_id)
    handler.on_chain_error(RuntimeError("boom"), run_id=run_id)

    assert len(fake.sent) == 1
    assert fake.sent[0]["error"] == "boom"
