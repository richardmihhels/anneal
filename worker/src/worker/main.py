"""Worker entrypoint for explicit demo and production modes."""

from __future__ import annotations

import asyncio
import logging
import os

from shared.models import Trace

from worker.models import CustomerConfig, PipelineComponents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required in production mode")
    return value


def _production_components() -> PipelineComponents:
    from core.clustering import AnthropicJudge, AnthropicLabeler, OpenAIEmbedder
    from core.eval import AnthropicEvalJudge, HttpAgentRunner
    from core.optimizer import GEPAMutator

    runner_url = _required("ANNEAL_AGENT_RUNNER_URL")
    return PipelineComponents(
        embedder=OpenAIEmbedder(os.environ.get("ANNEAL_EMBEDDING_MODEL", "text-embedding-3-small")),
        clustering_judge=AnthropicJudge(os.environ.get("ANNEAL_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")),
        labeler=AnthropicLabeler(os.environ.get("ANNEAL_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")),
        mutator=GEPAMutator(os.environ.get("ANNEAL_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")),
        eval_runner=HttpAgentRunner(
            runner_url,
            api_key=os.environ.get("ANNEAL_AGENT_RUNNER_API_KEY", ""),
        ),
        eval_judge=AnthropicEvalJudge(os.environ.get("ANNEAL_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")),
        mutation_budget=int(os.environ.get("ANNEAL_MUTATION_BUDGET", "4")),
    )


def _demo_customer() -> CustomerConfig:
    seed_contexts = ("issue resolved successfully",) * 10 + ("I cannot help with that",) * 10
    seed_labels = ("pass",) * 10 + ("fail",) * 10
    return CustomerConfig(
        organization_id="org_demo",
        agent_id="cascade-support-v1",
        repo="anneal-demo/support-agent",
        config_path="agent/prompts.py",
        baseline_prompt="anneal-baseline-v1",
        seed_contexts=seed_contexts,
        seed_labels=seed_labels,
    )


async def _run_demo(manual: bool) -> None:
    from core.github import FakeGitHubGateway
    from core.testing.generator import generate_dataset

    from worker.models import fake_components
    from worker.scheduler import setup_scheduler, trigger_now
    from worker.store import FakeRunStore

    customer = _demo_customer()
    gateway = FakeGitHubGateway()
    gateway.add_file(customer.repo, customer.config_path, customer.baseline_prompt)

    async def get_traces(_: str, __: str) -> list[Trace]:
        return generate_dataset(n=150, seed=42)

    customers = [customer]
    store = FakeRunStore()
    if manual:
        await trigger_now(customers, store, gateway, fake_components(), get_traces)
        return

    scheduler = setup_scheduler(customers, store, gateway, fake_components(), get_traces)
    scheduler.start()
    logger.info("Demo scheduler started — next run: Monday 02:00 UTC")
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()


async def _run_production(manual: bool) -> None:
    from core.db.repositories import PostgresTraceRepo
    from core.github import GitHubAppClient

    from worker.config import load_customers
    from worker.digest import SMTPDigestNotifier
    from worker.scheduler import setup_scheduler, trigger_now
    from worker.store import PostgresRunStore

    _required("OPENAI_API_KEY")
    _required("ANTHROPIC_API_KEY")
    postgres_url = _required("POSTGRES_URL")
    customers = load_customers()
    store = PostgresRunStore(postgres_url)
    trace_repo = PostgresTraceRepo(postgres_url)
    await store.migrate()
    await trace_repo.migrate()
    gateway = GitHubAppClient(
        int(_required("GITHUB_APP_ID")),
        _required("GITHUB_APP_PRIVATE_KEY").replace("\\n", "\n"),
    )
    components = _production_components()
    notifier = SMTPDigestNotifier() if os.environ.get("ANNEAL_SMTP_HOST") else None

    async def get_traces(organization_id: str, agent_id: str) -> list[Trace]:
        return await trace_repo.list_recent(organization_id, agent_id)

    try:
        if manual:
            await trigger_now(
                customers,
                store,
                gateway,
                components,
                get_traces,
                digest_notifier=notifier,
            )
            return

        scheduler = setup_scheduler(
            customers,
            store,
            gateway,
            components,
            get_traces,
            digest_notifier=notifier,
        )
        scheduler.start()
        logger.info("Production scheduler started — next run: Monday 02:00 UTC")
        try:
            await asyncio.Event().wait()
        finally:
            scheduler.shutdown()
    finally:
        await trace_repo.close()
        await store.close()


async def _run_production_alarms() -> None:
    from core.alarm import LoggingAlarmNotifier
    from core.alarm.notifier import SMTPEmailNotifier
    from core.alarm.store import PostgresAlarmStore
    from core.db.repositories import PostgresTraceRepo

    from worker.alarms import run_alarm_cycle
    from worker.config import load_customers

    postgres_url = _required("POSTGRES_URL")
    customers = load_customers()
    trace_repo = PostgresTraceRepo(postgres_url)
    alarm_store = PostgresAlarmStore(postgres_url)
    await trace_repo.migrate()
    notifier = SMTPEmailNotifier() if os.environ.get("ANNEAL_SMTP_HOST") else LoggingAlarmNotifier()

    async def get_traces(organization_id: str, agent_id: str) -> list[Trace]:
        return await trace_repo.list_recent(organization_id, agent_id, days=2)

    try:
        fired = await run_alarm_cycle(customers, get_traces, alarm_store, notifier)
        logger.info("Alarm cycle completed — %d alarm(s) fired", len(fired))
    finally:
        await trace_repo.close()
        await alarm_store.close()


async def _main() -> None:
    mode = os.environ.get("ANNEAL_MODE", "demo").strip().lower()
    task = os.environ.get("ANNEAL_TASK", "optimize").strip().lower()
    manual = os.environ.get("ANNEAL_TRIGGER_NOW", "").lower() in {"1", "true", "yes"}
    if mode == "demo":
        if task != "optimize":
            raise RuntimeError("Demo mode supports only ANNEAL_TASK=optimize")
        await _run_demo(manual)
    elif mode == "production":
        if task == "optimize":
            await _run_production(manual)
        elif task == "alarms":
            await _run_production_alarms()
        else:
            raise RuntimeError("ANNEAL_TASK must be either 'optimize' or 'alarms'")
    else:
        raise RuntimeError("ANNEAL_MODE must be either 'demo' or 'production'")


def run_optimization_cycle() -> None:
    """Synchronous entrypoint kept for backwards compatibility."""
    asyncio.run(_main())


if __name__ == "__main__":
    asyncio.run(_main())
