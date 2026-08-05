"""Organization-scoped read API consumed by the dashboard server."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from core.auth import require_organization
from core.db.repositories import DashboardRepo, DashboardSnapshot, FakeDashboardRepo

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_dashboard_repo: DashboardRepo = FakeDashboardRepo()


def get_dashboard_repo() -> DashboardRepo:
    return _dashboard_repo


def set_dashboard_repo(repo: DashboardRepo) -> None:
    global _dashboard_repo
    _dashboard_repo = repo


@router.get("/data")
async def dashboard_data(
    organization_id: Annotated[str, Depends(require_organization)],
    repo: Annotated[DashboardRepo, Depends(get_dashboard_repo)],
) -> DashboardSnapshot:
    return await repo.snapshot(organization_id)
