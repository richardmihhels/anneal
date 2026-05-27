"""V1 customer smoke: SDK trace -> ingest -> worker -> PR -> dashboard-scoped run."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from anneal_sdk.handler import AnnealCallbackHandler
from core.clustering.embedder import TFIDFEmbedder
from core.clustering.judge import FakeJudge
from core.clustering.labeler import FakeLabeler
from core.db.repositories import FakeSpanRepo, FakeTraceRepo
from core.eval.runner import AgentConfig
from core.github.client import FakeGitHubGateway
from core.main import app
from core.optimizer.mutator import FakeMutator
from core.routers.ingest import get_span_repo, get_trace_repo
from core.testing.generator import generate_dataset
from fastapi.testclient import TestClient
from shared.models import Trace
from worker.models import CustomerConfig, PipelineComponents
from worker.pipeline import run_optimization_cycle
from worker.store import FakeRunStore


class _CaptureClient:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def send_langsmith_run(self, run: dict[str, Any]) -> None:
        self.sent.append(run)


class _MutationAwareRunner:
    def run(self, trace: Trace, config: AgentConfig) -> str:
        return "issue resolved successfully." if "mutation" in config.prompt else "I cannot help with that."


class _KeywordJudge:
    def score(self, context: str) -> float:
        return 1.0 if "resolved" in context.lower() else 0.0


def _components() -> PipelineComponents:
    return PipelineComponents(
        embedder=TFIDFEmbedder(),
        clustering_judge=FakeJudge(),
        labeler=FakeLabeler(),
        mutator=FakeMutator(),
        eval_runner=_MutationAwareRunner(),  # type: ignore[arg-type]
        eval_judge=_KeywordJudge(),  # type: ignore[arg-type]
        mutation_budget=1,
    )


def _customer(org_id: str) -> CustomerConfig:
    seed_contexts = ["issue resolved successfully"] * 10 + ["I cannot help with that"] * 10
    seed_labels = ["pass"] * 10 + ["fail"] * 10
    return CustomerConfig(
        organization_id=org_id,
        agent_id="cascade-support-v1",
        repo="anneal-smoke/support-agent",
        config_path="agent/prompts.py",
        baseline_prompt="anneal-baseline-v1",
        seed_contexts=tuple(seed_contexts),
        seed_labels=tuple(seed_labels),
    )


def test_v1_customer_smoke_path() -> None:
    org_id = "org_smoke_customer"
    capture = _CaptureClient()
    handler = AnnealCallbackHandler(capture, agent_id="cascade-support-v1")  # type: ignore[arg-type]
    run_id = uuid.uuid4()

    handler.on_chain_start(
        {"name": "support_graph"},
        {"messages": [{"role": "user", "content": "Refund my SSO invoice"}]},
        run_id=run_id,
    )
    handler.on_chain_end({"content": "Resolved."}, run_id=run_id)
    assert len(capture.sent) == 1

    trace_repo = FakeTraceRepo()
    span_repo = FakeSpanRepo()
    app.dependency_overrides[get_trace_repo] = lambda: trace_repo
    app.dependency_overrides[get_span_repo] = lambda: span_repo
    try:
        with TestClient(app) as client:
            response = client.post(
                "/ingest/langsmith",
                json=capture.sent[0],
                headers={"X-Anneal-Org": org_id},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert trace_repo.saved[0].organization_id == org_id
    assert span_repo.saved[0]["organization_id"] == org_id

    customer = _customer(org_id)
    traces = [trace_repo.saved[0]] + [
        trace.model_copy(update={"organization_id": org_id}) for trace in generate_dataset(n=150, seed=42)
    ]
    store = FakeRunStore()
    gateway = FakeGitHubGateway()
    gateway.add_file(customer.repo, customer.config_path, customer.baseline_prompt)

    run = asyncio.run(
        run_optimization_cycle(
            customer=customer,
            traces=traces,
            store=store,
            gateway=gateway,
            components=_components(),
        )
    )

    assert run.status == "completed"
    assert run.organization_id == org_id
    assert gateway.opened_prs

    dashboard_visible_runs = [saved for saved in store.all_runs if saved.organization_id == org_id]
    assert dashboard_visible_runs == [run]
    events = asyncio.run(store.list_events(run.id))
    publishing = [event for event in events if event.stage == "publishing" and event.event == "completed"]
    assert publishing
    assert publishing[0].metadata["pr_urls"] == [pr["url"] for pr in gateway.opened_prs]
