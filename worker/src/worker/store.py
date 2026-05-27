from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from shared.models import Alarm, EvalResult, OptimizationRun, WeeklyDigest

from worker.models import RunEvent

logger = logging.getLogger(__name__)

# DDL — run once at startup via PostgresRunStore.migrate()
_DDL = """
CREATE TABLE IF NOT EXISTS optimization_runs (
    id          TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL DEFAULT 'org_demo',
    agent_id    TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    status      TEXT NOT NULL,
    cluster_ids JSONB NOT NULL DEFAULT '[]',
    proposed_change_ids JSONB NOT NULL DEFAULT '[]'
);

ALTER TABLE optimization_runs
    ADD COLUMN IF NOT EXISTS organization_id TEXT NOT NULL DEFAULT 'org_demo';

CREATE TABLE IF NOT EXISTS run_events (
    id       TEXT PRIMARY KEY,
    run_id   TEXT NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    stage    TEXT NOT NULL,
    event    TEXT NOT NULL,
    message  TEXT NOT NULL,
    ts       TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS run_events_run_id_ts ON run_events(run_id, ts);

CREATE TABLE IF NOT EXISTS eval_results (
    id                   TEXT PRIMARY KEY,
    optimization_run_id  TEXT REFERENCES optimization_runs(id) ON DELETE CASCADE,
    proposed_change_id   TEXT,
    run_at               TIMESTAMPTZ NOT NULL,
    baseline_score       DOUBLE PRECISION NOT NULL,
    candidate_score      DOUBLE PRECISION NOT NULL,
    delta                DOUBLE PRECISION NOT NULL,
    p_value              DOUBLE PRECISION NOT NULL,
    sample_size          INT NOT NULL,
    passed               BOOLEAN NOT NULL,
    judge_agreement_rate DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS eval_results_run_id_idx ON eval_results (optimization_run_id);
CREATE INDEX IF NOT EXISTS eval_results_run_at_idx ON eval_results (run_at DESC);

CREATE TABLE IF NOT EXISTS alarms (
    id                   TEXT PRIMARY KEY,
    organization_id      TEXT NOT NULL DEFAULT 'org_demo',
    agent_id             TEXT NOT NULL,
    category             TEXT NOT NULL,
    baseline_rate        DOUBLE PRECISION NOT NULL,
    current_rate         DOUBLE PRECISION NOT NULL,
    window_hours         INT NOT NULL,
    affected_trace_count INT NOT NULL,
    first_detected       TIMESTAMPTZ NOT NULL,
    cause_hypothesis     TEXT NOT NULL,
    notified             BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS alarms_agent_id_category_idx ON alarms (agent_id, category, first_detected DESC);

CREATE TABLE IF NOT EXISTS weekly_digests (
    id                   TEXT PRIMARY KEY,
    optimization_run_id  TEXT NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    organization_id      TEXT NOT NULL DEFAULT 'org_demo',
    agent_id             TEXT NOT NULL,
    week_start           TIMESTAMPTZ NOT NULL,
    week_end             TIMESTAMPTZ NOT NULL,
    generated_at         TIMESTAMPTZ NOT NULL,
    subject              TEXT NOT NULL,
    summary              TEXT NOT NULL,
    pr_shipped           BOOLEAN NOT NULL,
    pr_urls              JSONB NOT NULL DEFAULT '[]',
    health_direction     TEXT NOT NULL,
    alarm_ids            JSONB NOT NULL DEFAULT '[]',
    email_body           TEXT NOT NULL,
    page_body            TEXT NOT NULL,
    UNIQUE (optimization_run_id)
);

CREATE INDEX IF NOT EXISTS weekly_digests_org_week_idx ON weekly_digests (organization_id, week_end DESC);
"""


@runtime_checkable
class RunStore(Protocol):
    async def create_run(self, run: OptimizationRun) -> None: ...
    async def update_run(self, run: OptimizationRun) -> None: ...
    async def log_event(self, event: RunEvent) -> None: ...
    async def get_run(self, run_id: str) -> OptimizationRun | None: ...
    async def list_events(self, run_id: str) -> list[RunEvent]: ...
    async def save_eval_result(self, result: EvalResult) -> None: ...
    async def list_eval_results(
        self, agent_id: str, before: datetime, limit: int
    ) -> list[EvalResult]: ...
    async def list_alarms(
        self, organization_id: str, agent_id: str, start: datetime, end: datetime
    ) -> list[Alarm]: ...
    async def save_weekly_digest(self, digest: WeeklyDigest) -> None: ...
    async def get_weekly_digest_for_run(self, run_id: str) -> WeeklyDigest | None: ...


class FakeRunStore:
    """In-memory store for tests."""

    def __init__(self) -> None:
        self._runs: dict[str, OptimizationRun] = {}
        self._events: list[RunEvent] = []
        self._eval_results: list[EvalResult] = []
        self._alarms: list[Alarm] = []
        self._weekly_digests: list[WeeklyDigest] = []

    async def create_run(self, run: OptimizationRun) -> None:
        self._runs[run.id] = run

    async def update_run(self, run: OptimizationRun) -> None:
        self._runs[run.id] = run

    async def log_event(self, event: RunEvent) -> None:
        logger.info(
            "run=%s stage=%s event=%s msg=%s",
            event.run_id,
            event.stage,
            event.event,
            event.message,
        )
        self._events.append(event)

    async def get_run(self, run_id: str) -> OptimizationRun | None:
        return self._runs.get(run_id)

    async def list_events(self, run_id: str) -> list[RunEvent]:
        return [e for e in self._events if e.run_id == run_id]

    async def save_eval_result(self, result: EvalResult) -> None:
        self._eval_results.append(result)

    async def list_eval_results(
        self, agent_id: str, before: datetime, limit: int
    ) -> list[EvalResult]:
        run_ids = {
            run.id
            for run in self._runs.values()
            if run.agent_id == agent_id and run.created_at < before
        }
        return sorted(
            [er for er in self._eval_results if er.optimization_run_id in run_ids],
            key=lambda er: er.run_at,
            reverse=True,
        )[:limit]

    async def list_alarms(
        self, organization_id: str, agent_id: str, start: datetime, end: datetime
    ) -> list[Alarm]:
        return [
            alarm
            for alarm in self._alarms
            if alarm.organization_id == organization_id
            and alarm.agent_id == agent_id
            and start <= alarm.first_detected <= end
        ]

    async def save_weekly_digest(self, digest: WeeklyDigest) -> None:
        if await self.get_weekly_digest_for_run(digest.optimization_run_id) is None:
            self._weekly_digests.append(digest)

    async def get_weekly_digest_for_run(self, run_id: str) -> WeeklyDigest | None:
        for digest in self._weekly_digests:
            if digest.optimization_run_id == run_id:
                return digest
        return None

    @property
    def all_runs(self) -> list[OptimizationRun]:
        return list(self._runs.values())

    @property
    def all_events(self) -> list[RunEvent]:
        return list(self._events)

    @property
    def all_eval_results(self) -> list[EvalResult]:
        return list(self._eval_results)

    @property
    def all_weekly_digests(self) -> list[WeeklyDigest]:
        return list(self._weekly_digests)

    async def save_alarm(self, alarm: Alarm) -> None:
        self._alarms.append(alarm)


class PostgresRunStore:
    """Persist runs and timeline events to Postgres via asyncpg."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Any = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            import asyncpg  # type: ignore[import-untyped]

            self._pool = await asyncpg.create_pool(self._dsn)
        return self._pool

    async def migrate(self) -> None:
        """Create tables if they do not exist. Safe to call on every startup."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(_DDL)

    async def create_run(self, run: OptimizationRun) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO optimization_runs
                    (id, organization_id, agent_id, created_at, updated_at, status, cluster_ids, proposed_change_ids)
                VALUES ($1, $2, $3, $4, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                run.id,
                run.organization_id,
                run.agent_id,
                run.created_at,
                run.status,
                json.dumps(run.cluster_ids),
                json.dumps(run.proposed_change_ids),
            )

    async def update_run(self, run: OptimizationRun) -> None:
        from datetime import UTC, datetime

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE optimization_runs
                   SET updated_at = $2,
                       status = $3,
                       cluster_ids = $4,
                       proposed_change_ids = $5
                 WHERE id = $1
                """,
                run.id,
                datetime.now(UTC),
                run.status,
                json.dumps(run.cluster_ids),
                json.dumps(run.proposed_change_ids),
            )

    async def log_event(self, event: RunEvent) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO run_events (id, run_id, stage, event, message, ts, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                event.id,
                event.run_id,
                event.stage,
                event.event,
                event.message,
                event.ts,
                json.dumps(event.metadata),
            )

    async def get_run(self, run_id: str) -> OptimizationRun | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM optimization_runs WHERE id = $1", run_id)
        if row is None:
            return None
        return OptimizationRun(
            id=row["id"],
            organization_id=row["organization_id"],
            agent_id=row["agent_id"],
            created_at=row["created_at"],
            status=row["status"],
            cluster_ids=json.loads(row["cluster_ids"]),
            proposed_change_ids=json.loads(row["proposed_change_ids"]),
        )

    async def list_events(self, run_id: str) -> list[RunEvent]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM run_events WHERE run_id = $1 ORDER BY ts", run_id)
        return [
            RunEvent(
                id=row["id"],
                run_id=row["run_id"],
                stage=row["stage"],
                event=row["event"],
                message=row["message"],
                ts=row["ts"],
                metadata=json.loads(row["metadata"]),
            )
            for row in rows
        ]

    async def save_eval_result(self, result: EvalResult) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO eval_results
                    (id, optimization_run_id, proposed_change_id, run_at,
                     baseline_score, candidate_score, delta, p_value,
                     sample_size, passed, judge_agreement_rate)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO NOTHING
                """,
                result.id,
                result.optimization_run_id,
                result.proposed_change_id,
                result.run_at,
                result.baseline_score,
                result.candidate_score,
                result.delta,
                result.p_value,
                result.sample_size,
                result.passed,
                result.judge_agreement_rate,
            )

    async def list_eval_results(
        self, agent_id: str, before: datetime, limit: int
    ) -> list[EvalResult]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT er.*
                  FROM eval_results er
                  JOIN optimization_runs r ON r.id = er.optimization_run_id
                 WHERE r.agent_id = $1
                   AND r.created_at < $2
                 ORDER BY er.run_at DESC
                 LIMIT $3
                """,
                agent_id,
                before,
                limit,
            )
        return [
            EvalResult(
                id=row["id"],
                optimization_run_id=row["optimization_run_id"],
                proposed_change_id=row["proposed_change_id"],
                run_at=row["run_at"],
                baseline_score=row["baseline_score"],
                candidate_score=row["candidate_score"],
                delta=row["delta"],
                p_value=row["p_value"],
                sample_size=row["sample_size"],
                passed=row["passed"],
                judge_agreement_rate=row["judge_agreement_rate"],
            )
            for row in rows
        ]

    async def list_alarms(
        self, organization_id: str, agent_id: str, start: datetime, end: datetime
    ) -> list[Alarm]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM alarms
                 WHERE organization_id = $1
                   AND agent_id = $2
                   AND first_detected >= $3
                   AND first_detected <= $4
                 ORDER BY first_detected DESC
                """,
                organization_id,
                agent_id,
                start,
                end,
            )
        return [
            Alarm(
                id=row["id"],
                organization_id=row["organization_id"],
                agent_id=row["agent_id"],
                category=row["category"],
                baseline_rate=row["baseline_rate"],
                current_rate=row["current_rate"],
                window_hours=row["window_hours"],
                affected_trace_count=row["affected_trace_count"],
                first_detected=row["first_detected"],
                cause_hypothesis=row["cause_hypothesis"],
                notified=row["notified"],
            )
            for row in rows
        ]

    async def save_weekly_digest(self, digest: WeeklyDigest) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO weekly_digests
                    (id, optimization_run_id, organization_id, agent_id,
                     week_start, week_end, generated_at, subject, summary,
                     pr_shipped, pr_urls, health_direction, alarm_ids,
                     email_body, page_body)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (optimization_run_id) DO NOTHING
                """,
                digest.id,
                digest.optimization_run_id,
                digest.organization_id,
                digest.agent_id,
                digest.week_start,
                digest.week_end,
                digest.generated_at,
                digest.subject,
                digest.summary,
                digest.pr_shipped,
                json.dumps(digest.pr_urls),
                digest.health_direction,
                json.dumps(digest.alarm_ids),
                digest.email_body,
                digest.page_body,
            )

    async def get_weekly_digest_for_run(self, run_id: str) -> WeeklyDigest | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM weekly_digests WHERE optimization_run_id = $1", run_id)
        if row is None:
            return None
        return WeeklyDigest(
            id=row["id"],
            optimization_run_id=row["optimization_run_id"],
            organization_id=row["organization_id"],
            agent_id=row["agent_id"],
            week_start=row["week_start"],
            week_end=row["week_end"],
            generated_at=row["generated_at"],
            subject=row["subject"],
            summary=row["summary"],
            pr_shipped=row["pr_shipped"],
            pr_urls=json.loads(row["pr_urls"]),
            health_direction=row["health_direction"],
            alarm_ids=json.loads(row["alarm_ids"]),
            email_body=row["email_body"],
            page_body=row["page_body"],
        )
