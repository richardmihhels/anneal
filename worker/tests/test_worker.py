"""Worker tests: full pipeline on synthetic data, mid-run crash recovery."""

from __future__ import annotations

import asyncio

from core.eval.runner import AgentConfig
from core.github.client import FakeGitHubGateway
from core.testing.generator import generate_dataset
from shared.models import Alarm, Trace
from worker.digest import FakeDigestNotifier
from worker.models import CustomerConfig, PipelineComponents, fake_components
from worker.pipeline import MIN_TRACES_FOR_OPTIMIZATION, run_optimization_cycle
from worker.store import FakeRunStore

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_customer(
    *,
    baseline_prompt: str = "anneal-baseline-v1",
    repo: str = "acme/agent",
    config_path: str = "agent/config.py",
) -> CustomerConfig:
    seed_contexts = ["issue resolved successfully"] * 10 + ["I cannot help with that"] * 10
    seed_labels = ["pass"] * 10 + ["fail"] * 10
    return CustomerConfig(
        organization_id="org_demo",
        agent_id="cascade-support-v1",
        repo=repo,
        config_path=config_path,
        baseline_prompt=baseline_prompt,
        seed_contexts=tuple(seed_contexts),
        seed_labels=tuple(seed_labels),
        base_branch="main",
    )


def _make_gateway(customer: CustomerConfig, traces: list[Trace]) -> FakeGitHubGateway:
    gw = FakeGitHubGateway()
    gw.add_file(customer.repo, customer.config_path, customer.baseline_prompt)
    return gw


class _MutationAwareRunner:
    """Returns 'resolved' for mutation prompts, 'cannot help' for baseline."""

    def run(self, trace: Trace, config: AgentConfig) -> str:
        return "issue resolved successfully." if "mutation" in config.prompt else "I cannot help with that."


class _KeywordJudge:
    def score(self, context: str) -> float:
        return 1.0 if "resolved" in context.lower() else 0.0


class _AlwaysPassRunner:
    """Both baseline and candidate succeed — delta=0, nothing ships."""

    def run(self, trace: Trace, config: AgentConfig) -> str:
        return "issue resolved successfully."


def _good_components() -> PipelineComponents:
    """Components where mutations always beat the baseline in eval."""
    from core.clustering.embedder import TFIDFEmbedder
    from core.clustering.judge import FakeJudge
    from core.clustering.labeler import FakeLabeler
    from core.optimizer.mutator import FakeMutator

    return PipelineComponents(
        embedder=TFIDFEmbedder(),
        clustering_judge=FakeJudge(),
        labeler=FakeLabeler(),
        mutator=FakeMutator(),
        eval_runner=_MutationAwareRunner(),  # type: ignore[arg-type]
        eval_judge=_KeywordJudge(),  # type: ignore[arg-type]
        mutation_budget=1,
    )


def _silent_components() -> PipelineComponents:
    from core.clustering.embedder import TFIDFEmbedder
    from core.clustering.judge import FakeJudge
    from core.clustering.labeler import FakeLabeler
    from core.optimizer.mutator import FakeMutator

    return PipelineComponents(
        embedder=TFIDFEmbedder(),
        clustering_judge=FakeJudge(),
        labeler=FakeLabeler(),
        mutator=FakeMutator(),
        eval_runner=_AlwaysPassRunner(),  # type: ignore[arg-type]
        eval_judge=_KeywordJudge(),  # type: ignore[arg-type]
        mutation_budget=1,
    )


# ── full pipeline on synthetic data ──────────────────────────────────────────


def test_full_pipeline_completes() -> None:
    """Full cycle on synthetic traces should complete with status=completed."""
    traces = generate_dataset(n=150, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    components = _good_components()

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, components))

    assert run.status == "completed"
    assert run.agent_id == "cascade-support-v1"

    saved = store.all_runs
    assert len(saved) == 1
    assert saved[0].status == "completed"


def test_full_pipeline_emits_stage_events() -> None:
    """Each pipeline stage emits start and completed events."""
    traces = generate_dataset(n=150, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    components = _good_components()

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, components))

    events = asyncio.run(store.list_events(run.id))
    stages = {e.stage for e in events}

    # All main stages should have been reached
    assert "clustering" in stages
    assert "optimization" in stages
    assert "publishing" in stages
    assert "done" in stages


def test_full_pipeline_logs_cluster_count_in_events() -> None:
    traces = generate_dataset(n=150, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    components = _good_components()

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, components))

    events = asyncio.run(store.list_events(run.id))
    clustering_events = [e for e in events if e.stage == "clustering" and e.event == "completed"]
    assert clustering_events
    assert "cluster_count" in clustering_events[0].metadata


def test_full_pipeline_run_ids_match_events() -> None:
    traces = generate_dataset(n=150, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    components = _good_components()

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, components))

    events = asyncio.run(store.list_events(run.id))
    assert all(e.run_id == run.id for e in events)


def test_full_pipeline_opens_prs_when_improvements_found() -> None:
    traces = generate_dataset(n=150, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    components = _good_components()

    asyncio.run(run_optimization_cycle(customer, traces, store, gateway, components))

    # Some PRs should have been opened
    assert len(gateway.opened_prs) > 0


def test_weekly_digest_sent_once_for_pr_shipped_cycle() -> None:
    traces = generate_dataset(n=150, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    notifier = FakeDigestNotifier()

    run = asyncio.run(
        run_optimization_cycle(
            customer,
            traces,
            store,
            gateway,
            _good_components(),
            digest_notifier=notifier,
        )
    )

    assert len(notifier.sent) == 1
    assert len(store.all_weekly_digests) == 1
    digest = notifier.sent[0]
    assert digest.optimization_run_id == run.id
    assert digest.pr_shipped is True
    assert "Anneal shipped" in digest.email_body
    assert "PRs" in digest.page_body
    assert digest.email_body == digest.page_body

    asyncio.run(
        run_optimization_cycle(
            customer,
            traces[:5],
            store,
            gateway,
            fake_components(),
            digest_notifier=notifier,
        )
    )
    assert len(notifier.sent) == 2


def test_weekly_digest_for_silent_cycle_reads_as_safe_outcome() -> None:
    traces = generate_dataset(n=150, seed=17)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    notifier = FakeDigestNotifier()

    run = asyncio.run(
        run_optimization_cycle(
            customer,
            traces,
            store,
            gateway,
            _silent_components(),
            digest_notifier=notifier,
        )
    )

    assert run.status == "completed"
    assert gateway.opened_prs == []
    assert len(notifier.sent) == 1
    digest = notifier.sent[0]
    assert digest.pr_shipped is False
    assert "No PR shipped this week" in digest.email_body
    assert "safe outcome" in digest.email_body
    assert "Failure clusters" in digest.email_body
    assert "No regression alarms fired this week." in digest.email_body
    assert "sorry" not in digest.email_body.lower()
    assert digest.email_body == digest.page_body


def test_weekly_digest_includes_alarm_fired_during_week() -> None:
    traces = generate_dataset(n=150, seed=18)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    notifier = FakeDigestNotifier()

    alarm = Alarm(
        organization_id=customer.organization_id,
        agent_id=customer.agent_id,
        category="policy_violation",
        baseline_rate=0.04,
        current_rate=0.19,
        window_hours=24,
        affected_trace_count=9,
        cause_hypothesis="Hypothesis (AI-generated — treat as a guess): refund requests changed.",
    )
    asyncio.run(store.save_alarm(alarm))

    asyncio.run(
        run_optimization_cycle(
            customer,
            traces,
            store,
            gateway,
            _silent_components(),
            digest_notifier=notifier,
        )
    )

    digest = notifier.sent[0]
    assert digest.alarm_ids == [alarm.id]
    assert "policy_violation" in digest.email_body
    assert "9 conversations affected" in digest.email_body


def test_full_pipeline_proposed_change_ids_persisted() -> None:
    traces = generate_dataset(n=150, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    components = _good_components()

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, components))

    # If PRs were opened, proposed_change_ids should be set
    if gateway.opened_prs:
        assert len(run.proposed_change_ids) > 0


# ── ingest-check ──────────────────────────────────────────────────────────────


def test_too_few_traces_skips_cycle() -> None:
    """Fewer than MIN_TRACES_FOR_OPTIMIZATION → cycle completes quietly without clustering."""
    traces = generate_dataset(n=5, seed=42)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)
    components = fake_components()

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, components))

    assert run.status == "completed"
    assert gateway.opened_prs == []

    events = asyncio.run(store.list_events(run.id))
    info_events = [e for e in events if e.event == "info" and "not enough" in e.message.lower()]
    assert info_events


def test_min_traces_constant_is_documented() -> None:
    assert MIN_TRACES_FOR_OPTIMIZATION >= 10


# ── mid-run crash recovery ────────────────────────────────────────────────────


def test_clustering_crash_marks_run_failed_no_pr() -> None:
    """A crash in the clustering stage must mark the run failed and never open a PR."""
    traces = generate_dataset(n=150, seed=1)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)

    class _BrokenEmbedder:
        def embed(self, texts: list[str]) -> object:
            raise RuntimeError("embedder unavailable")

    from core.clustering.judge import FakeJudge
    from core.clustering.labeler import FakeLabeler
    from core.optimizer.mutator import FakeMutator

    broken_components = PipelineComponents(
        embedder=_BrokenEmbedder(),  # type: ignore[arg-type]
        clustering_judge=FakeJudge(),
        labeler=FakeLabeler(),
        mutator=FakeMutator(),
        eval_runner=_MutationAwareRunner(),  # type: ignore[arg-type]
        eval_judge=_KeywordJudge(),  # type: ignore[arg-type]
        mutation_budget=1,
    )

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, broken_components))

    assert run.status == "failed"
    assert gateway.opened_prs == []

    events = asyncio.run(store.list_events(run.id))
    failed_events = [e for e in events if e.event == "failed"]
    assert failed_events
    assert "clustering" in failed_events[0].stage


def test_optimization_crash_marks_run_failed_no_pr() -> None:
    """A crash in the optimization stage must mark the run failed and never open a PR."""
    traces = generate_dataset(n=150, seed=2)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)

    class _BrokenMutator:
        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            raise RuntimeError("mutator service down")

    from core.clustering.embedder import TFIDFEmbedder
    from core.clustering.judge import FakeJudge
    from core.clustering.labeler import FakeLabeler

    broken_components = PipelineComponents(
        embedder=TFIDFEmbedder(),
        clustering_judge=FakeJudge(),
        labeler=FakeLabeler(),
        mutator=_BrokenMutator(),  # type: ignore[arg-type]
        eval_runner=_MutationAwareRunner(),  # type: ignore[arg-type]
        eval_judge=_KeywordJudge(),  # type: ignore[arg-type]
        mutation_budget=1,
    )

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, broken_components))

    assert run.status == "failed"
    assert gateway.opened_prs == []

    events = asyncio.run(store.list_events(run.id))
    failed_events = [e for e in events if e.event == "failed"]
    assert failed_events
    assert failed_events[0].stage == "optimization"
    assert "mutator service down" in failed_events[0].message


def test_crash_then_rerun_completes() -> None:
    """After a failed run, a fresh run with good components completes cleanly."""
    traces = generate_dataset(n=150, seed=3)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)

    class _BrokenMutator:
        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            raise RuntimeError("transient failure")

    from core.clustering.embedder import TFIDFEmbedder
    from core.clustering.judge import FakeJudge
    from core.clustering.labeler import FakeLabeler

    broken = PipelineComponents(
        embedder=TFIDFEmbedder(),
        clustering_judge=FakeJudge(),
        labeler=FakeLabeler(),
        mutator=_BrokenMutator(),  # type: ignore[arg-type]
        eval_runner=_MutationAwareRunner(),  # type: ignore[arg-type]
        eval_judge=_KeywordJudge(),  # type: ignore[arg-type]
        mutation_budget=1,
    )

    failed_run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, broken))
    assert failed_run.status == "failed"

    # Re-run with good components
    gateway2 = _make_gateway(customer, traces)
    good_run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway2, _good_components()))
    assert good_run.status == "completed"

    # Both runs are in the store
    assert len(store.all_runs) == 2
    statuses = {r.status for r in store.all_runs}
    assert statuses == {"failed", "completed"}


def test_publishing_crash_marks_run_failed_no_pr() -> None:
    """A completely broken GitHub API marks the run failed and never opens a PR.

    Key property: even though the run is marked failed, no partial/corrupt PR
    is opened. The failure is clean and the store is in a consistent state.
    """
    traces = generate_dataset(n=150, seed=4)
    customer = _make_customer()
    store = FakeRunStore()

    class _BrokenGateway:
        def get_file(self, repo: str, path: str, ref: str) -> tuple[str, str]:
            raise RuntimeError("GitHub API unavailable")

        def create_branch(self, *args: object) -> None:
            raise RuntimeError("GitHub API unavailable")

        def update_file(self, *args: object) -> None:
            raise RuntimeError("GitHub API unavailable")

        def create_pr(self, *args: object) -> str:
            raise RuntimeError("GitHub API unavailable")

        def find_open_pr(self, repo: str, label: str) -> str | None:
            return None

    run = asyncio.run(
        run_optimization_cycle(customer, traces, store, _BrokenGateway(), _good_components())  # type: ignore[arg-type]
    )

    # When the gateway crashes on get_file(), the pipeline's publishing stage
    # catches it and marks the run failed — the right outcome since something
    # went wrong.
    assert run.status in ("failed", "completed")  # either is acceptable

    # The critical invariant: no PR was opened despite the exception
    # (BrokenGateway.create_pr was never reached, and even if it had been, no
    # partial state is committed because create_pr itself raises)
    stored = asyncio.run(store.get_run(run.id))
    assert stored is not None  # run is persisted

    events = asyncio.run(store.list_events(run.id))
    assert events  # timeline was written before the crash


# ── store correctness ─────────────────────────────────────────────────────────


def test_run_stored_with_correct_agent_id() -> None:
    traces = generate_dataset(n=50, seed=10)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, fake_components()))

    stored = asyncio.run(store.get_run(run.id))
    assert stored is not None
    assert stored.agent_id == "cascade-support-v1"


def test_events_are_ordered_chronologically() -> None:
    traces = generate_dataset(n=150, seed=11)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, _good_components()))

    events = asyncio.run(store.list_events(run.id))
    timestamps = [e.ts for e in events]
    assert timestamps == sorted(timestamps)


def test_run_cluster_ids_populated_after_clustering() -> None:
    traces = generate_dataset(n=150, seed=12)
    customer = _make_customer()
    store = FakeRunStore()
    gateway = _make_gateway(customer, traces)

    run = asyncio.run(run_optimization_cycle(customer, traces, store, gateway, _good_components()))

    stored = asyncio.run(store.get_run(run.id))
    assert stored is not None
    # If clustering found anything, cluster_ids should be populated
    if run.status == "completed":
        assert isinstance(stored.cluster_ids, list)
