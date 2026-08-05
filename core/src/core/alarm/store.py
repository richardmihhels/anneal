"""Alarm persistence: protocol + in-memory fake + Postgres implementation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from shared.models import Alarm


@runtime_checkable
class AlarmStore(Protocol):
    async def save_alarm(self, alarm: Alarm) -> None: ...
    async def get_recent_alarm(
        self,
        organization_id: str,
        agent_id: str,
        category: str,
        within_hours: int,
    ) -> Alarm | None: ...


class FakeAlarmStore:
    """In-memory store for tests."""

    def __init__(self) -> None:
        self._alarms: list[Alarm] = []

    async def save_alarm(self, alarm: Alarm) -> None:
        self._alarms.append(alarm)

    async def get_recent_alarm(
        self,
        organization_id: str,
        agent_id: str,
        category: str,
        within_hours: int,
    ) -> Alarm | None:
        cutoff = datetime.now(UTC) - timedelta(hours=within_hours)
        for alarm in reversed(self._alarms):
            if (
                alarm.organization_id == organization_id
                and alarm.agent_id == agent_id
                and alarm.category == category
                and alarm.first_detected >= cutoff
            ):
                return alarm
        return None

    @property
    def all_alarms(self) -> list[Alarm]:
        return list(self._alarms)


class PostgresAlarmStore:
    """Persist alarms to Postgres via asyncpg."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Any = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            import asyncpg  # type: ignore[import-untyped]

            self._pool = await asyncpg.create_pool(self._dsn)
        return self._pool

    async def save_alarm(self, alarm: Alarm) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO alarms
                    (id, organization_id, agent_id, category,
                     baseline_rate, current_rate, window_hours,
                     affected_trace_count, first_detected,
                     cause_hypothesis, notified)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO NOTHING
                """,
                alarm.id,
                alarm.organization_id,
                alarm.agent_id,
                alarm.category,
                alarm.baseline_rate,
                alarm.current_rate,
                alarm.window_hours,
                alarm.affected_trace_count,
                alarm.first_detected,
                alarm.cause_hypothesis,
                alarm.notified,
            )

    async def get_recent_alarm(
        self,
        organization_id: str,
        agent_id: str,
        category: str,
        within_hours: int,
    ) -> Alarm | None:
        cutoff = datetime.now(UTC) - timedelta(hours=within_hours)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM alarms
                WHERE organization_id = $1
                  AND agent_id = $2
                  AND category = $3
                  AND first_detected >= $4
                ORDER BY first_detected DESC
                LIMIT 1
                """,
                organization_id,
                agent_id,
                category,
                cutoff,
            )
        if row is None:
            return None
        return Alarm(
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

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
