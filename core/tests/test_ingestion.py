"""Round-trip ingestion tests for OTel and LangSmith formats, plus scrubbing."""

from __future__ import annotations

import pytest
from core.db.repositories import FakeSpanRepo, FakeTraceRepo
from core.ingestion import normalize_langsmith, normalize_otel
from core.ingestion.scrub import scrub as core_scrub
from core.main import app
from core.routers.ingest import get_span_repo, get_trace_repo
from fastapi.testclient import TestClient

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def fake_trace_repo() -> FakeTraceRepo:
    return FakeTraceRepo()


@pytest.fixture()
def fake_span_repo() -> FakeSpanRepo:
    return FakeSpanRepo()


@pytest.fixture()
def client(fake_trace_repo: FakeTraceRepo, fake_span_repo: FakeSpanRepo) -> TestClient:
    app.dependency_overrides[get_trace_repo] = lambda: fake_trace_repo
    app.dependency_overrides[get_span_repo] = lambda: fake_span_repo
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── OTel normalizer ───────────────────────────────────────────────────────────

OTEL_PAYLOAD = {
    "resourceSpans": [
        {
            "resource": {
                "attributes": [
                    {"key": "agent.id", "value": {"stringValue": "my-agent-v1"}},
                    {"key": "session.id", "value": {"stringValue": "sess-abc"}},
                ]
            },
            "scopeSpans": [
                {
                    "spans": [
                        {
                            "traceId": "abcdef1234567890abcdef1234567890",
                            "spanId": "abcdef1234567891",
                            "name": "agent_turn",
                            "startTimeUnixNano": "1711468800000000000",
                            "endTimeUnixNano": "1711468801720000000",
                            "attributes": [
                                {"key": "input", "value": {"stringValue": '{"messages": []}'}},
                                {"key": "output", "value": {"stringValue": '{"content": "hello"}'}},
                            ],
                            "status": {"code": 0},
                        }
                    ]
                }
            ],
        }
    ]
}


def test_otel_normalizer_produces_trace() -> None:
    traces = normalize_otel(OTEL_PAYLOAD)
    assert len(traces) == 1
    trace = traces[0]
    assert trace.agent_id == "my-agent-v1"
    assert trace.session_id == "sess-abc"
    assert len(trace.spans) == 1
    span = trace.spans[0]
    assert span.name == "agent_turn"
    assert span.duration_ms == pytest.approx(1720.0)
    assert span.output == {"content": "hello"}


def test_otel_round_trip(
    client: TestClient,
    fake_trace_repo: FakeTraceRepo,
    fake_span_repo: FakeSpanRepo,
) -> None:
    resp = client.post("/ingest/otel", json=OTEL_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingested"] == 1
    assert len(fake_trace_repo.saved) == 1
    assert len(fake_span_repo.saved) == 1


def test_otel_empty_payload_returns_422(client: TestClient) -> None:
    resp = client.post("/ingest/otel", json={"resourceSpans": []})
    assert resp.status_code == 422


# ── LangSmith normalizer ──────────────────────────────────────────────────────

LANGSMITH_PAYLOAD: dict = {
    "id": "run-aaaa-bbbb-cccc-dddd",
    "session_id": "sess-xyz",
    "name": "support_agent",
    "run_type": "chain",
    "start_time": "2025-03-26T16:00:00Z",
    "end_time": "2025-03-26T16:00:06Z",
    "inputs": {"messages": [{"role": "user", "content": "Hello"}]},
    "outputs": {"content": "Hi there!"},
    "error": None,
    "tags": ["agent_id:cascade-support-v1"],
    "extra": {"metadata": {"customer_tier": "pro"}},
    "child_runs": [
        {
            "id": "run-child-0001",
            "name": "tool:search_kb",
            "run_type": "tool",
            "start_time": "2025-03-26T16:00:01Z",
            "end_time": "2025-03-26T16:00:02Z",
            "inputs": {"query": "rate limits"},
            "outputs": {"articles": []},
            "error": None,
            "tags": [],
            "extra": {},
            "child_runs": [],
        }
    ],
}


def test_langsmith_normalizer_produces_trace() -> None:
    trace = normalize_langsmith(LANGSMITH_PAYLOAD)
    assert trace.id == "sess-xyz"
    assert trace.agent_id == "cascade-support-v1"
    assert len(trace.spans) == 2  # parent + 1 child
    parent = trace.spans[0]
    assert parent.name == "support_agent"
    assert parent.duration_ms == pytest.approx(6000.0)


def test_langsmith_round_trip(
    client: TestClient,
    fake_trace_repo: FakeTraceRepo,
    fake_span_repo: FakeSpanRepo,
) -> None:
    resp = client.post("/ingest/langsmith", json=LANGSMITH_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingested"] == 1
    assert len(fake_trace_repo.saved) == 1
    assert len(fake_span_repo.saved) == 2  # parent + child span


# ── scrubbing ─────────────────────────────────────────────────────────────────


def test_scrub_redacts_api_key_values() -> None:
    payload = {
        "extra": {
            "metadata": {
                "api_key": "sk-abc123def456ghi789jkl012mno345",
                "model": "gpt-4",
            }
        }
    }
    result = core_scrub(payload)
    assert result["extra"]["metadata"]["api_key"] == "[REDACTED]"
    assert result["extra"]["metadata"]["model"] == "gpt-4"


def test_scrub_redacts_bearer_tokens_in_strings() -> None:
    payload = {"auth": "Bearer eyJhbGciOiJSUzI1NiJ9.verylongtoken12345678"}
    result = core_scrub(payload)
    assert "[REDACTED]" in result["auth"]


def test_scrub_redacts_anthropic_key_in_string() -> None:
    payload = {"msg": "using key sk-ant-api03-supersecretkey1234567890abcdef"}
    result = core_scrub(payload)
    assert "sk-ant" not in result["msg"]


def test_scrub_preserves_non_secret_fields() -> None:
    payload = {"model": "gpt-4", "temperature": 0.7, "messages": [{"role": "user", "content": "hi"}]}
    result = core_scrub(payload)
    assert result == payload


def test_scrub_handles_nested_lists() -> None:
    payload = {
        "runs": [
            {"api_key": "sk-openai12345678901234567890abcdef", "name": "run1"},
            {"api_key": "", "name": "run2"},
        ]
    }
    result = core_scrub(payload)
    assert result["runs"][0]["api_key"] == "[REDACTED]"
    assert result["runs"][1]["api_key"] == ""  # empty string not redacted
    assert result["runs"][0]["name"] == "run1"


def test_ingest_otel_scrubs_secrets(
    client: TestClient,
    fake_trace_repo: FakeTraceRepo,
) -> None:
    """Secrets in OTel span attributes must be scrubbed before persistence."""
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "agent.id", "value": {"stringValue": "my-agent-v1"}},
                        {"key": "session.id", "value": {"stringValue": "sess-secret"}},
                        {"key": "api_key", "value": {"stringValue": "sk-secret12345678901234567890abcdef"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                                "spanId": "bbbbbbbbbbbbbbbb",
                                "name": "llm_call",
                                "startTimeUnixNano": "1711468800000000000",
                                "endTimeUnixNano": "1711468801000000000",
                                "attributes": [],
                                "status": {"code": 0},
                            }
                        ]
                    }
                ],
            }
        ]
    }
    resp = client.post("/ingest/otel", json=payload)
    assert resp.status_code == 200
    saved = fake_trace_repo.saved[0]
    assert "sk-secret" not in str(saved.metadata)
