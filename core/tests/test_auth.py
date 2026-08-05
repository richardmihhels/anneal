from __future__ import annotations

import pytest
from core.db.repositories import FakeSpanRepo, FakeTraceRepo
from core.main import app
from core.routers.ingest import get_span_repo, get_trace_repo
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("ANNEAL_API_KEYS_JSON", raising=False)
    monkeypatch.delenv("ANNEAL_API_KEY", raising=False)
    monkeypatch.delenv("ANNEAL_ORG_ID", raising=False)
    monkeypatch.setenv("ANNEAL_ENV", "development")
    app.dependency_overrides[get_trace_repo] = FakeTraceRepo
    app.dependency_overrides[get_span_repo] = FakeSpanRepo
    yield TestClient(app)
    app.dependency_overrides.clear()


def _payload() -> dict[str, object]:
    return {
        "id": "auth-run",
        "session_id": "auth-session",
        "name": "support_agent",
        "run_type": "chain",
        "start_time": "2025-03-26T16:00:00Z",
        "end_time": "2025-03-26T16:00:01Z",
        "inputs": {},
        "outputs": {"content": "ok"},
        "tags": ["agent_id:support-v1"],
        "extra": {"metadata": {"organization_id": "org_spoofed"}},
        "child_runs": [],
    }


def test_development_is_zero_config(client: TestClient) -> None:
    response = client.post("/ingest/langsmith", json=_payload(), headers={"X-Anneal-Org": "org_dev"})
    assert response.status_code == 200


def test_production_without_keys_fails_closed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANNEAL_ENV", "production")
    response = client.post("/ingest/langsmith", json=_payload(), headers={"X-Anneal-Org": "org_acme"})
    assert response.status_code == 503


def test_configured_key_authenticates_and_scopes_org(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    trace_repo = FakeTraceRepo()
    app.dependency_overrides[get_trace_repo] = lambda: trace_repo
    monkeypatch.setenv("ANNEAL_API_KEYS_JSON", '{"org_acme":"secret-acme"}')

    response = client.post(
        "/ingest/langsmith",
        json=_payload(),
        headers={"X-Anneal-Org": "org_acme", "Authorization": "Bearer secret-acme"},
    )

    assert response.status_code == 200
    assert trace_repo.saved[0].organization_id == "org_acme"


def test_wrong_key_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANNEAL_API_KEYS_JSON", '{"org_acme":"secret-acme"}')
    response = client.post(
        "/ingest/langsmith",
        json=_payload(),
        headers={"X-Anneal-Org": "org_acme", "Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_unknown_org_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANNEAL_API_KEYS_JSON", '{"org_acme":"secret-acme"}')
    response = client.post(
        "/ingest/langsmith",
        json=_payload(),
        headers={"X-Anneal-Org": "org_other", "Authorization": "Bearer secret-acme"},
    )
    assert response.status_code == 403
