"""Worker entrypoint — starts the scheduler or runs a manual trigger."""

from __future__ import annotations

import asyncio
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


async def _main() -> None:
    from core.github.client import FakeGitHubGateway
    from worker.models import CustomerConfig, fake_components
    from worker.scheduler import setup_scheduler, trigger_now
    from worker.store import FakeRunStore

    # In production, load from env / config file and use real implementations.
    # Here we wire up fakes so the worker can start without external services.
    customers: list[CustomerConfig] = []
    store = FakeRunStore()
    gateway = FakeGitHubGateway()
    components = fake_components()

    async def _get_traces(agent_id: str) -> list[object]:
        from core.testing.generator import generate_dataset

        return generate_dataset(n=100, seed=42)  # type: ignore[return-value]

    manual = os.environ.get("ANNEAL_TRIGGER_NOW", "").lower() in ("1", "true", "yes")

    if manual:
        logger.info("ANNEAL_TRIGGER_NOW set — running immediately")
        await trigger_now(customers, store, gateway, components, _get_traces)  # type: ignore[arg-type]
    else:
        scheduler = setup_scheduler(customers, store, gateway, components, _get_traces)  # type: ignore[arg-type]
        scheduler.start()
        logger.info("Scheduler started — next run: Monday 02:00 UTC")
        try:
            await asyncio.Event().wait()  # run forever
        finally:
            scheduler.shutdown()


def run_optimization_cycle() -> None:
    """Synchronous entrypoint kept for backwards compatibility with existing tests."""
    asyncio.run(_main())


if __name__ == "__main__":
    asyncio.run(_main())
