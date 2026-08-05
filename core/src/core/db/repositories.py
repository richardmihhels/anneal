from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from urllib.parse import unquote, urlparse

from shared.models import Span, Trace


@runtime_checkable
class TraceRepo(Protocol):
    async def save(self, trace: Trace) -> None: ...


@runtime_checkable
class SpanRepo(Protocol):
    async def save_many(
        self,
        spans: list[Span],
        organization_id: str,
        agent_id: str,
        session_id: str,
    ) -> None: ...


# ── in-memory fakes used in tests ────────────────────────────────────────────


class FakeTraceRepo:
    def __init__(self) -> None:
        self.saved: list[Trace] = []

    async def save(self, trace: Trace) -> None:
        self.saved.append(trace)


class FakeSpanRepo:
    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    async def save_many(
        self,
        spans: list[Span],
        organization_id: str,
        agent_id: str,
        session_id: str,
    ) -> None:
        for s in spans:
            self.saved.append(
                {
                    "trace_id": s.trace_id,
                    "span_id": s.id,
                    "organization_id": organization_id,
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "name": s.name,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration_ms": s.duration_ms,
                    "input": json.dumps(s.input),
                    "output": json.dumps(s.output),
                    "error": s.error,
                    "metadata": json.dumps(s.metadata),
                }
            )


# ── real implementations (require DB connections in env) ──────────────────────


class PostgresTraceRepo:
    """Persist trace metadata rows to Postgres via asyncpg."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Any = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            import asyncpg  # type: ignore[import-untyped]

            self._pool = await asyncpg.create_pool(self._dsn)
        return self._pool

    async def migrate(self) -> None:
        sql = Path(__file__).with_name("postgres.sql").read_text(encoding="utf-8")
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(sql)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def save(self, trace: Trace) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO traces
                    (id, organization_id, agent_id, session_id, created_at, outcome, metadata, payload)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (organization_id, id) DO UPDATE SET
                    outcome = EXCLUDED.outcome,
                    metadata = EXCLUDED.metadata,
                    payload = EXCLUDED.payload
                """,
                trace.id,
                trace.organization_id,
                trace.agent_id,
                trace.session_id,
                trace.created_at,
                trace.outcome,
                json.dumps(trace.metadata),
                trace.model_dump_json(),
            )

    async def list_recent(
        self,
        organization_id: str,
        agent_id: str,
        *,
        days: int = 7,
        limit: int = 10_000,
    ) -> list[Trace]:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT payload
                  FROM traces
                 WHERE organization_id = $1
                   AND agent_id = $2
                   AND created_at >= $3
                 ORDER BY created_at DESC
                 LIMIT $4
                """,
                organization_id,
                agent_id,
                cutoff,
                limit,
            )
        return [
            Trace.model_validate_json(row["payload"])
            if isinstance(row["payload"], str)
            else Trace.model_validate(row["payload"])
            for row in rows
        ]


class ClickHouseSpanRepo:
    """Insert spans into ClickHouse via clickhouse-connect."""

    def __init__(
        self,
        host: str,
        port: int = 8123,
        *,
        username: str = "default",
        password: str = "",
        secure: bool = False,
        database: str = "anneal",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._secure = secure
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", database):
            raise ValueError("ClickHouse database name contains invalid characters")
        self._database = database
        self._client: Any = None

    @classmethod
    def from_url(cls, url: str, *, password: str = "", database: str = "anneal") -> ClickHouseSpanRepo:
        parsed = urlparse(url)
        if not parsed.hostname:
            raise ValueError("CLICKHOUSE_URL must include a hostname")
        secure = parsed.scheme == "https"
        return cls(
            parsed.hostname,
            parsed.port or (8443 if secure else 8123),
            username=unquote(parsed.username or "default"),
            password=password or unquote(parsed.password or ""),
            secure=secure,
            database=parsed.path.lstrip("/") or database,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            import clickhouse_connect  # type: ignore[import-untyped]

            self._client = clickhouse_connect.get_client(
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                secure=self._secure,
                database="default",
            )
        return self._client

    async def migrate(self) -> None:
        sql = Path(__file__).with_name("clickhouse.sql").read_text(encoding="utf-8")
        for statement in sql.format(database=self._database).split(";"):
            if statement.strip():
                self._get_client().command(statement)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def save_many(
        self,
        spans: list[Span],
        organization_id: str,
        agent_id: str,
        session_id: str,
    ) -> None:
        if not spans:
            return
        client = self._get_client()
        rows = [
            [
                s.trace_id,
                s.id,
                organization_id,
                agent_id,
                session_id,
                s.name,
                s.start_time,
                s.end_time,
                s.duration_ms,
                json.dumps(s.input),
                json.dumps(s.output),
                s.error,
                json.dumps(s.metadata),
            ]
            for s in spans
        ]
        client.insert(
            f"{self._database}.spans",
            rows,
            column_names=[
                "trace_id",
                "span_id",
                "organization_id",
                "agent_id",
                "session_id",
                "name",
                "start_time",
                "end_time",
                "duration_ms",
                "input",
                "output",
                "error",
                "metadata",
            ],
        )


DashboardSnapshot = dict[str, list[dict[str, Any]]]


@runtime_checkable
class DashboardRepo(Protocol):
    async def snapshot(self, organization_id: str) -> DashboardSnapshot: ...


def _row_dict(row: Any, json_fields: tuple[str, ...] = ()) -> dict[str, Any]:
    data = dict(row)
    for field in json_fields:
        value = data.get(field)
        if isinstance(value, str):
            data[field] = json.loads(value)
    return data


class FakeDashboardRepo:
    def __init__(self, data: DashboardSnapshot | None = None) -> None:
        self._data = data or {
            "runs": [],
            "events": [],
            "clusters": [],
            "proposed_changes": [],
            "eval_results": [],
            "alarms": [],
            "weekly_digests": [],
        }
        self.requested_organizations: list[str] = []

    async def snapshot(self, organization_id: str) -> DashboardSnapshot:
        self.requested_organizations.append(organization_id)
        return self._data


class PostgresDashboardRepo:
    """Read an organization-scoped dashboard snapshot from Postgres."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Any = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            import asyncpg

            self._pool = await asyncpg.create_pool(self._dsn)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def snapshot(self, organization_id: str) -> DashboardSnapshot:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            runs = await conn.fetch(
                "SELECT * FROM optimization_runs WHERE organization_id = $1 ORDER BY created_at DESC",
                organization_id,
            )
            run_ids = [row["id"] for row in runs]
            events: list[Any] = []
            clusters: list[Any] = []
            changes: list[Any] = []
            eval_results: list[Any] = []
            digests: list[Any] = []
            if run_ids:
                events = await conn.fetch(
                    "SELECT * FROM run_events WHERE run_id = ANY($1::text[]) ORDER BY ts",
                    run_ids,
                )
                clusters = await conn.fetch(
                    "SELECT * FROM failure_clusters WHERE optimization_run_id = ANY($1::text[])",
                    run_ids,
                )
                changes = await conn.fetch(
                    "SELECT * FROM proposed_changes WHERE optimization_run_id = ANY($1::text[])",
                    run_ids,
                )
                eval_results = await conn.fetch(
                    "SELECT * FROM eval_results WHERE optimization_run_id = ANY($1::text[]) ORDER BY run_at",
                    run_ids,
                )
                digests = await conn.fetch(
                    "SELECT * FROM weekly_digests WHERE optimization_run_id = ANY($1::text[]) ORDER BY week_end DESC",
                    run_ids,
                )
            alarms = await conn.fetch(
                "SELECT * FROM alarms WHERE organization_id = $1 ORDER BY first_detected DESC",
                organization_id,
            )

        return {
            "runs": [_row_dict(row, ("cluster_ids", "proposed_change_ids")) for row in runs],
            "events": [_row_dict(row, ("metadata",)) for row in events],
            "clusters": [_row_dict(row, ("trace_ids",)) for row in clusters],
            "proposed_changes": [_row_dict(row) for row in changes],
            "eval_results": [_row_dict(row) for row in eval_results],
            "alarms": [_row_dict(row) for row in alarms],
            "weekly_digests": [_row_dict(row, ("pr_urls", "alarm_ids")) for row in digests],
        }
