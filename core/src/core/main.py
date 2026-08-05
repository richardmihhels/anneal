from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.auth import validate_auth_configuration
from core.db.repositories import (
    ClickHouseSpanRepo,
    FakeSpanRepo,
    PostgresDashboardRepo,
    PostgresTraceRepo,
)
from core.routers.dashboard import router as dashboard_router
from core.routers.dashboard import set_dashboard_repo
from core.routers.ingest import router as ingest_router
from core.routers.ingest import set_repos


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    postgres_url = os.environ.get("POSTGRES_URL", "").strip()
    clickhouse_url = os.environ.get("CLICKHOUSE_URL", "").strip()
    environment = os.environ.get("ANNEAL_ENV", "development").strip().lower()
    validate_auth_configuration()

    trace_repo: PostgresTraceRepo | None = None
    span_repo: ClickHouseSpanRepo | None = None
    dashboard_repo: PostgresDashboardRepo | None = None

    if postgres_url:
        trace_repo = PostgresTraceRepo(postgres_url)
        await trace_repo.migrate()
        set_repos(trace_repo, FakeSpanRepo())
        dashboard_repo = PostgresDashboardRepo(postgres_url)
        set_dashboard_repo(dashboard_repo)

        if clickhouse_url:
            span_repo = ClickHouseSpanRepo.from_url(
                clickhouse_url,
                password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
                database=os.environ.get("CLICKHOUSE_DB", "anneal"),
            )
            await span_repo.migrate()
            set_repos(trace_repo, span_repo)
        elif environment == "production":
            raise RuntimeError("CLICKHOUSE_URL is required in production")
    elif environment == "production":
        raise RuntimeError("POSTGRES_URL is required in production")

    try:
        yield
    finally:
        if dashboard_repo is not None:
            await dashboard_repo.close()
        if span_repo is not None:
            await span_repo.close()
        if trace_repo is not None:
            await trace_repo.close()


app = FastAPI(title="Anneal API", version="0.1.0", lifespan=lifespan)
app.include_router(ingest_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
