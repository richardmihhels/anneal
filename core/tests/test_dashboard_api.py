from __future__ import annotations

import pytest
from core.db.repositories import FakeDashboardRepo
from core.main import app
from core.routers.dashboard import get_dashboard_repo
from fastapi.testclient import TestClient


def test_dashboard_snapshot_is_authenticated_and_org_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANNEAL_API_KEYS_JSON", '{"org_acme":"secret-acme"}')
    repo = FakeDashboardRepo(
        {
            "runs": [],
            "events": [],
            "clusters": [],
            "proposed_changes": [],
            "eval_results": [],
            "alarms": [],
            "weekly_digests": [],
        }
    )
    app.dependency_overrides[get_dashboard_repo] = lambda: repo
    try:
        response = TestClient(app).get(
            "/dashboard/data",
            headers={"X-Anneal-Org": "org_acme", "Authorization": "Bearer secret-acme"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["runs"] == []
    assert repo.requested_organizations == ["org_acme"]
