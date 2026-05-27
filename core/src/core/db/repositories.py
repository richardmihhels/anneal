from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

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

    async def save(self, trace: Trace) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO traces (id, organization_id, agent_id, session_id, created_at, outcome, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                trace.id,
                trace.organization_id,
                trace.agent_id,
                trace.session_id,
                trace.created_at,
                trace.outcome,
                json.dumps(trace.metadata),
            )


class ClickHouseSpanRepo:
    """Insert spans into ClickHouse via clickhouse-connect."""

    def __init__(self, host: str, port: int = 8123) -> None:
        self._host = host
        self._port = port
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import clickhouse_connect  # type: ignore[import-untyped]

            self._client = clickhouse_connect.get_client(host=self._host, port=self._port)
        return self._client

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
            "spans",
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
