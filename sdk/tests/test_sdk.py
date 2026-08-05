"""SDK tests for scrubbing, delivery, and the real LangChain callback contract."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import anneal_sdk.client as client_module
from anneal_sdk import AnnealClient
from anneal_sdk.handler import AnnealCallbackHandler
from anneal_sdk.scrub import scrub
from langchain_core.callbacks import BaseCallbackHandler, CallbackManager
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, LLMResult

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


def test_scrub_converts_langchain_and_common_python_values_to_json() -> None:
    data = {
        "message": HumanMessage(content="hello"),
        "at": datetime(2026, 8, 4, 12, 0, tzinfo=UTC),
        "run_id": uuid.uuid4(),
        "labels": ("one", "two"),
    }

    result = scrub(data)

    assert result["message"]["content"] == "hello"
    assert result["at"] == "2026-08-04T12:00:00+00:00"
    assert result["run_id"] == str(data["run_id"])
    assert result["labels"] == ["one", "two"]
    json.dumps(result)


def test_sdk_imports_without_optional_langchain_dependency() -> None:
    script = """
import importlib.abc
import sys

class BlockLangChain(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "langchain_core" or fullname.startswith("langchain_core."):
            raise ModuleNotFoundError(fullname)
        return None

sys.meta_path.insert(0, BlockLangChain())
from anneal_sdk import AnnealCallbackHandler
assert AnnealCallbackHandler.__name__ == "AnnealCallbackHandler"
"""

    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)


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


def test_client_reuses_http_connection_and_checks_status(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeResponse:
        def __init__(self) -> None:
            self.status_checked = False

        def raise_for_status(self) -> None:
            self.status_checked = True

    class FakeHTTPClient:
        instances: list[FakeHTTPClient] = []
        posts: list[tuple[str, dict[str, Any], dict[str, str], FakeResponse]] = []

        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout
            self.closed = False
            self.instances.append(self)

        def post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]) -> FakeResponse:
            response = FakeResponse()
            self.posts.append((url, json, headers, response))
            return response

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(client_module.httpx, "Client", FakeHTTPClient)

    client = AnnealClient("http://anneal.test", api_key="ann_test", timeout=3.0)
    client.send_langsmith_run({"id": "run-1"})
    client.send_langsmith_run({"id": "run-2"})
    client.close()

    assert len(FakeHTTPClient.instances) == 1
    assert FakeHTTPClient.instances[0].timeout == 3.0
    assert FakeHTTPClient.instances[0].closed
    assert [post[1]["id"] for post in FakeHTTPClient.posts] == ["run-1", "run-2"]
    assert all(post[3].status_checked for post in FakeHTTPClient.posts)


# ── callback handler ──────────────────────────────────────────────────────────


class _FakeClient:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def send_langsmith_run(self, run: dict[str, Any]) -> None:
        self.sent.append(run)


def test_handler_flushes_on_chain_end() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")
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


def test_handler_preserves_run_metadata() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")
    run_id = uuid.uuid4()

    handler.on_chain_start(
        {"name": "support_chain"},
        {"messages": []},
        run_id=run_id,
        metadata={"outcome": "failure", "failure_category": "wrong_tool"},
    )
    handler.on_chain_end({"content": "done"}, run_id=run_id)

    assert fake.sent[0]["extra"]["metadata"] == {
        "agent_id": "test-agent",
        "outcome": "failure",
        "failure_category": "wrong_tool",
    }


def test_handler_child_runs_nested() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")
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
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()

    handler.on_chain_start({"name": "parent"}, {}, run_id=parent_id)
    handler.on_tool_start({"name": "tool"}, "x", run_id=child_id, parent_run_id=parent_id)
    handler.on_tool_end("y", run_id=child_id)

    # Parent not ended yet — nothing sent
    assert len(fake.sent) == 0


def test_handler_error_still_flushes() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")
    run_id = uuid.uuid4()

    handler.on_chain_start({"name": "chain"}, {}, run_id=run_id)
    handler.on_chain_error(RuntimeError("boom"), run_id=run_id)

    assert len(fake.sent) == 1
    assert fake.sent[0]["error"] == "boom"


def test_handler_works_through_langchain_callback_manager() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")
    manager = CallbackManager([handler])
    run_id = uuid.uuid4()

    run_manager = manager.on_chain_start(
        {"name": "support_chain"},
        {"messages": [HumanMessage(content="hello")]},
        run_id=run_id,
    )
    run_manager.on_chain_end({"messages": [AIMessage(content="done")]})

    assert isinstance(handler, BaseCallbackHandler)
    assert fake.sent[0]["inputs"]["messages"][0]["content"] == "hello"
    assert fake.sent[0]["outputs"]["messages"][0]["content"] == "done"
    json.dumps(fake.sent[0])


def test_handler_captures_chat_model_runs() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")
    manager = CallbackManager([handler])

    run_manager = manager.on_chat_model_start(
        {"name": "chat_model"},
        [[HumanMessage(content="hello")]],
        run_id=uuid.uuid4(),
    )[0]
    run_manager.on_llm_end(LLMResult(generations=[[ChatGeneration(message=AIMessage(content="answer"))]]))

    run = fake.sent[0]
    assert run["run_type"] == "llm"
    assert run["inputs"]["messages"][0][0]["content"] == "hello"
    assert run["outputs"]["generations"][0][0]["message"]["content"] == "answer"
    json.dumps(run)


def test_handler_accepts_parallel_top_level_runs() -> None:
    fake = _FakeClient()
    handler = AnnealCallbackHandler(fake, agent_id="test-agent")

    def emit(index: int) -> None:
        run_id = uuid.uuid4()
        handler.on_chain_start({"name": f"run-{index}"}, {"index": index}, run_id=run_id)
        handler.on_chain_end({"index": index}, run_id=run_id)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(emit, range(100)))

    assert len(fake.sent) == 100
    assert {run["name"] for run in fake.sent} == {f"run-{index}" for index in range(100)}
