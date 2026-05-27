"""Weekly job scheduler and manual trigger."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from shared.models import Trace

from core.github.client import GitHubGateway
from worker.models import CustomerConfig, PipelineComponents
from worker.pipeline import run_optimization_cycle
from worker.store import RunStore

logger = logging.getLogger(__name__)


def setup_scheduler(
    customers: list[CustomerConfig],
    store: RunStore,
    gateway: GitHubGateway,
    components: PipelineComponents,
    get_traces: Callable[[str], Coroutine[Any, Any, list[Trace]]],
) -> Any:
    """Return a configured APScheduler AsyncIOScheduler, not yet started.

    The scheduler runs the optimization cycle for all customers every Monday at
    02:00 UTC. Call `scheduler.start()` after the event loop is running.

    Args:
        customers:   List of customer configurations to optimize.
        store:       Persistence backend for runs and events.
        gateway:     GitHub API client (real or fake).
        components:  ML/LLM components (fake for tests, real for production).
        get_traces:  Async callable(agent_id) → list[Trace]. In production this
                     queries ClickHouse; in tests it returns synthetic data.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
    from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

    scheduler: Any = AsyncIOScheduler()

    async def _job() -> None:
        logger.info("Weekly optimization job started for %d customer(s)", len(customers))
        for customer in customers:
            traces = await get_traces(customer.agent_id)
            await run_optimization_cycle(customer, traces, store, gateway, components)

    scheduler.add_job(
        _job,
        trigger=CronTrigger(day_of_week="mon", hour=2, minute=0, timezone="UTC"),
        id="weekly_optimization",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1h late start
    )

    return scheduler


async def trigger_now(
    customers: list[CustomerConfig],
    store: RunStore,
    gateway: GitHubGateway,
    components: PipelineComponents,
    get_traces: Callable[[str], Coroutine[Any, Any, list[Trace]]],
) -> None:
    """Run the optimization cycle immediately for all customers (manual trigger)."""
    logger.info("Manual trigger: running optimization for %d customer(s)", len(customers))
    for customer in customers:
        traces = await get_traces(customer.agent_id)
        run = await run_optimization_cycle(customer, traces, store, gateway, components)
        logger.info(
            "customer=%s run=%s status=%s",
            customer.agent_id,
            run.id,
            run.status,
        )
