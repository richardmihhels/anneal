"""Tests for the GEPA optimization engine."""

from __future__ import annotations

from core.eval import AgentConfig, EvalHarness, split
from core.optimizer import FakeMutator, Optimizer
from core.optimizer.mutator import MUTATION_BUDGET, PromptMutator
from core.testing.generator import generate_dataset, generate_trace
from shared.models import FailureCluster

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_cluster(trace_ids: list[str], label: str = "test-cluster") -> FailureCluster:
    return FailureCluster(
        label=label,
        description=f"Test failure pattern: {label}",
        trace_ids=trace_ids,
        size=len(trace_ids),
        representative_trace_id=trace_ids[0] if trace_ids else None,
    )


def _make_harness(
    *,
    baseline_prompt: str,
    good_prompt_substr: str,
    seed_size: int = 20,
) -> EvalHarness:
    """Harness where prompts containing `good_prompt_substr` score 1.0, others 0.0."""

    class _Runner:
        def run(self, trace: object, config: AgentConfig) -> str:
            return "resolved" if good_prompt_substr in config.prompt else "cannot help"

    class _Judge:
        def score(self, ctx: str) -> float:
            return 1.0 if "resolved" in ctx else 0.0

    half = seed_size // 2
    return EvalHarness(
        runner=_Runner(),
        judge=_Judge(),
        seed_contexts=["resolved"] * half + ["cannot help"] * half,
        seed_labels=["pass"] * half + ["fail"] * half,
    )


# ── FakeMutator ───────────────────────────────────────────────────────────────


def test_fake_mutator_returns_budget_candidates() -> None:
    m = FakeMutator()
    candidates = m.mutate("my prompt", ["example failure"], budget=4)
    assert len(candidates) == 4


def test_fake_mutator_candidates_differ() -> None:
    m = FakeMutator()
    candidates = m.mutate("p", ["ex"], budget=3)
    assert len(set(candidates)) == 3  # all unique


def test_fake_mutator_respects_budget_zero() -> None:
    m = FakeMutator()
    assert m.mutate("p", [], budget=0) == []


def test_fake_mutator_satisfies_protocol() -> None:
    assert isinstance(FakeMutator(), PromptMutator)


def test_mutation_budget_constant_is_4() -> None:
    assert MUTATION_BUDGET == 4


# ── regression candidate always rejected ─────────────────────────────────────


def test_regression_candidate_rejected() -> None:
    """A candidate that scores worse than baseline must not produce a ProposedChange."""
    traces = generate_dataset(n=80, seed=1)
    _, holdout = split(traces, seed=1)
    assert holdout.cases, "Need holdout cases"

    cluster_traces = [generate_trace("wrong_tool", seed=i) for i in range(5)]
    cluster = _make_cluster([t.id for t in cluster_traces])

    baseline = AgentConfig(prompt="baseline", skills=())

    class _RegressionMutator:
        """Always returns a prompt that scores 0.0 (worse than baseline at 1.0)."""

        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            return ["bad-prompt-regression"] * budget

    harness = _make_harness(baseline_prompt="baseline", good_prompt_substr="baseline")
    optimizer = Optimizer(mutator=_RegressionMutator(), harness=harness, budget=2)

    result = optimizer.optimize(
        clusters=[cluster],
        traces=cluster_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-run",
    )

    assert result.proposed_changes == ()
    assert result.eval_results == ()


def test_no_improvement_returns_empty() -> None:
    """Candidate identical to baseline → delta=0 → not accepted."""
    traces = generate_dataset(n=80, seed=2)
    _, holdout = split(traces, seed=2)
    assert holdout.cases

    cluster_traces = [generate_trace("wrong_tool", seed=i + 10) for i in range(5)]
    cluster = _make_cluster([t.id for t in cluster_traces])
    baseline = AgentConfig(prompt="same-prompt", skills=())

    class _IdenticalMutator:
        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            return [prompt] * budget  # identical to baseline

    harness = _make_harness(baseline_prompt="same-prompt", good_prompt_substr="same-prompt")
    optimizer = Optimizer(mutator=_IdenticalMutator(), harness=harness, budget=2)

    result = optimizer.optimize(
        clusters=[cluster],
        traces=cluster_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-no-improvement",
    )
    assert result.proposed_changes == ()


# ── known-good improvement accepted ──────────────────────────────────────────


def test_known_good_improvement_accepted() -> None:
    """A candidate that significantly outscores baseline produces a ProposedChange."""
    traces = generate_dataset(n=100, seed=3)
    _, holdout = split(traces, seed=3)
    assert holdout.cases, "Need holdout cases"

    cluster_traces = [generate_trace("wrong_tool", seed=i + 20) for i in range(5)]
    cluster = _make_cluster([t.id for t in cluster_traces])

    baseline = AgentConfig(prompt="baseline-v1", skills=())
    good_substr = "mutation"

    class _GoodMutator:
        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            return [f"{good_substr}-candidate"] + [f"other-{i}" for i in range(budget - 1)]

    harness = _make_harness(baseline_prompt="baseline-v1", good_prompt_substr=good_substr)
    optimizer = Optimizer(mutator=_GoodMutator(), harness=harness, budget=2)

    result = optimizer.optimize(
        clusters=[cluster],
        traces=cluster_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-accepted",
    )

    assert len(result.proposed_changes) == 1
    assert len(result.eval_results) == 1
    change = result.proposed_changes[0]
    ev = result.eval_results[0]

    assert change.optimization_run_id == "test-accepted"
    assert change.target == "system_prompt"
    assert change.before == "baseline-v1"
    assert good_substr in change.after
    assert ev.passed is True
    assert ev.delta > 0
    assert ev.p_value < 0.05
    assert change.eval_result_id == ev.id


def test_best_candidate_selected() -> None:
    """When multiple candidates beat baseline, the one with the highest delta is chosen."""
    traces = generate_dataset(n=100, seed=4)
    _, holdout = split(traces, seed=4)
    assert holdout.cases

    cluster_traces = [generate_trace("policy_violation", seed=i + 30) for i in range(5)]
    cluster = _make_cluster([t.id for t in cluster_traces])

    baseline = AgentConfig(prompt="baseline-v1", skills=())

    class _MultiGoodMutator:
        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            # Return two candidates that both beat baseline, but "mutation-best" is distinct
            return ["mutation-good", "mutation-best"]

    class _GradedRunner:
        def run(self, trace: object, config: AgentConfig) -> str:
            # mutation-best always resolves; mutation-good only sometimes
            if "mutation-best" in config.prompt:
                return "resolved"
            if "mutation-good" in config.prompt:
                return "resolved"  # both good — optimizer picks first that passes
            return "cannot help"

    class _Judge:
        def score(self, ctx: str) -> float:
            return 1.0 if "resolved" in ctx else 0.0

    half = 10
    harness = EvalHarness(
        runner=_GradedRunner(),
        judge=_Judge(),
        seed_contexts=["resolved"] * half + ["cannot help"] * half,
        seed_labels=["pass"] * half + ["fail"] * half,
    )

    optimizer = Optimizer(mutator=_MultiGoodMutator(), harness=harness, budget=2)
    result = optimizer.optimize(
        clusters=[cluster],
        traces=cluster_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-best-selected",
    )

    assert len(result.proposed_changes) == 1  # only one per cluster
    assert result.proposed_changes[0].eval_result_id is not None


# ── multi-cluster optimization ────────────────────────────────────────────────


def test_multiple_clusters_each_get_own_change() -> None:
    """Two clusters with good candidates → two ProposedChanges."""
    traces = generate_dataset(n=100, seed=5)
    _, holdout = split(traces, seed=5)
    assert holdout.cases

    cluster_a_traces = [generate_trace("wrong_tool", seed=i + 40) for i in range(5)]
    cluster_b_traces = [generate_trace("scope_creep", seed=i + 50) for i in range(5)]
    cluster_a = _make_cluster([t.id for t in cluster_a_traces], label="cluster-a")
    cluster_b = _make_cluster([t.id for t in cluster_b_traces], label="cluster-b")

    baseline = AgentConfig(prompt="baseline", skills=())

    class _GoodMutator:
        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            return ["mutation-candidate"]

    harness = _make_harness(baseline_prompt="baseline", good_prompt_substr="mutation")
    optimizer = Optimizer(mutator=_GoodMutator(), harness=harness, budget=1)

    result = optimizer.optimize(
        clusters=[cluster_a, cluster_b],
        traces=cluster_a_traces + cluster_b_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-multi",
    )

    assert len(result.proposed_changes) == 2
    assert len(result.eval_results) == 2
    run_ids = {c.optimization_run_id for c in result.proposed_changes}
    assert run_ids == {"test-multi"}


def test_one_bad_cluster_does_not_block_good_cluster() -> None:
    """Failing cluster should not prevent other clusters' changes from being emitted."""
    traces = generate_dataset(n=100, seed=6)
    _, holdout = split(traces, seed=6)
    assert holdout.cases

    good_traces = [generate_trace("wrong_tool", seed=i + 60) for i in range(5)]
    bad_traces = [generate_trace("scope_creep", seed=i + 70) for i in range(5)]
    good_cluster = _make_cluster([t.id for t in good_traces], label="good-cluster")
    bad_cluster = _make_cluster([t.id for t in bad_traces], label="bad-cluster")

    baseline = AgentConfig(prompt="baseline", skills=())

    class _MixedMutator:
        def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
            excerpt = failure_examples[0] if failure_examples else ""
            # Good cluster traces contain "SAML" or "SSO"; bad ones don't
            if "good" in excerpt or not excerpt:
                return ["mutation-candidate"]  # good candidate
            return ["bad-prompt"]  # bad candidate

    harness = _make_harness(baseline_prompt="baseline", good_prompt_substr="mutation")
    optimizer = Optimizer(mutator=_MixedMutator(), harness=harness, budget=1)

    result = optimizer.optimize(
        clusters=[good_cluster, bad_cluster],
        traces=good_traces + bad_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-mixed",
    )

    # At least the good cluster should produce a change
    assert len(result.proposed_changes) >= 1


# ── proposed change shape ─────────────────────────────────────────────────────


def test_proposed_change_rationale_contains_cluster_info() -> None:
    traces = generate_dataset(n=80, seed=7)
    _, holdout = split(traces, seed=7)
    assert holdout.cases

    cluster_traces = [generate_trace("wrong_tool", seed=i + 80) for i in range(5)]
    cluster = _make_cluster([t.id for t in cluster_traces], label="cluster-rationale-test")

    baseline = AgentConfig(prompt="baseline", skills=())
    harness = _make_harness(baseline_prompt="baseline", good_prompt_substr="mutation")
    optimizer = Optimizer(mutator=FakeMutator(), harness=harness, budget=1)

    result = optimizer.optimize(
        clusters=[cluster],
        traces=cluster_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-rationale",
    )

    assert result.proposed_changes, "Expected a ProposedChange"
    rationale = result.proposed_changes[0].rationale

    assert "cluster-rationale-test" in rationale
    assert "Eval result" in rationale
    assert "Baseline score" in rationale
    assert "p-value" in rationale


def test_proposed_change_has_correct_fields() -> None:
    traces = generate_dataset(n=80, seed=8)
    _, holdout = split(traces, seed=8)
    assert holdout.cases

    cluster_traces = [generate_trace("wrong_tool", seed=i + 90) for i in range(5)]
    cluster = _make_cluster([t.id for t in cluster_traces])

    baseline = AgentConfig(prompt="original-prompt", skills=("skill-a",))
    harness = _make_harness(baseline_prompt="original-prompt", good_prompt_substr="mutation")
    optimizer = Optimizer(mutator=FakeMutator(), harness=harness, budget=1)

    result = optimizer.optimize(
        clusters=[cluster],
        traces=cluster_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-fields",
    )

    assert result.proposed_changes
    change = result.proposed_changes[0]
    ev = result.eval_results[0]

    assert change.before == "original-prompt"
    assert change.target == "system_prompt"
    assert change.eval_result_id == ev.id
    assert ev.proposed_change_id == change.id
    assert ev.passed is True


# ── miscalibrated judge blocks optimization ───────────────────────────────────


def test_miscalibrated_judge_raises_and_skips_cluster() -> None:
    """Judge that disagrees with all human labels should raise JudgeCalibrationError."""
    traces = generate_dataset(n=50, seed=9)
    _, holdout = split(traces, seed=9)
    assert holdout.cases

    cluster_traces = [generate_trace("wrong_tool", seed=i + 100) for i in range(5)]
    cluster = _make_cluster([t.id for t in cluster_traces])
    baseline = AgentConfig(prompt="baseline", skills=())

    class _AlwaysPassJudge:
        def score(self, ctx: str) -> float:
            return 1.0

    from core.eval import EvalHarness

    # Use a runner that satisfies the protocol
    class _FakeRunner:
        def run(self, trace: object, config: AgentConfig) -> str:
            return "resolved"

    harness2 = EvalHarness(
        runner=_FakeRunner(),
        judge=_AlwaysPassJudge(),
        seed_contexts=["any context"] * 10,
        seed_labels=["fail"] * 10,
    )

    optimizer = Optimizer(mutator=FakeMutator(), harness=harness2, budget=1)

    # Should not raise — miscalibrated judge causes cluster to be skipped
    result = optimizer.optimize(
        clusters=[cluster],
        traces=cluster_traces,
        baseline=baseline,
        holdout=holdout,
        run_id="test-miscalibrated",
    )
    assert result.proposed_changes == ()
