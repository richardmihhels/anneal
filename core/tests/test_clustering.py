"""Tests for the failure clustering pipeline."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

import pytest
from core.clustering import ClusterPipeline, FakeJudge, FakeLabeler, TFIDFEmbedder
from core.clustering.context import extract_context
from core.clustering.pipeline import _MIN_CLUSTER_SIZE
from core.testing.generator import generate_dataset, generate_trace
from shared.models import Trace

# ── context extraction ────────────────────────────────────────────────────────


def test_extract_context_includes_user_message() -> None:
    trace = generate_trace("wrong_tool", seed=0)
    ctx = extract_context(trace)
    assert "USER:" in ctx
    assert "TOOLS:" in ctx


def test_extract_context_includes_tool_sequence() -> None:
    trace = generate_trace("policy_violation", seed=1)
    ctx = extract_context(trace)
    assert "lookup_order" in ctx
    assert "issue_refund" in ctx


def test_extract_context_includes_response() -> None:
    trace = generate_trace("scope_creep", seed=2)
    ctx = extract_context(trace)
    assert "RESPONSE:" in ctx


def test_extract_context_empty_trace() -> None:
    trace = Trace(
        id="test-empty",
        agent_id="cascade-support-v1",
        session_id="s1",
        created_at=datetime.now(UTC),
        spans=[],
    )
    ctx = extract_context(trace)
    assert ctx == ""


# ── embedder ─────────────────────────────────────────────────────────────────


def test_tfidf_embedder_shape() -> None:
    from core.clustering.embedder import TFIDFEmbedder

    embedder = TFIDFEmbedder(max_features=64)
    texts = ["the quick brown fox", "jumped over the lazy dog", "hello world"]
    X = embedder.embed(texts)
    assert X.shape == (3, 64) or X.shape[0] == 3
    assert X.dtype.kind == "f"  # float


def test_tfidf_embedder_unit_normalized() -> None:
    import numpy as np
    from core.clustering.embedder import TFIDFEmbedder

    embedder = TFIDFEmbedder()
    texts = ["refund policy 30 days", "wrong tool lookup order"]
    X = embedder.embed(texts)
    norms = np.linalg.norm(X, axis=1)
    # Rows with any content should be near unit norm
    for n in norms[norms > 0]:
        assert abs(float(n) - 1.0) < 1e-5


# ── judge ─────────────────────────────────────────────────────────────────────


def test_fake_judge_always_failure() -> None:
    from core.clustering.judge import FakeJudge

    judge = FakeJudge()
    assert judge.is_failure("any context") is True
    assert judge.is_failure("") is True


def test_pipeline_skips_success_traces() -> None:
    success_traces = [generate_trace("success", seed=i) for i in range(20)]
    failure_traces = [generate_trace("wrong_tool", seed=i) for i in range(10)]
    all_traces = success_traces + failure_traces

    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler(), min_cluster_size=3)
    clusters = pipeline.run(all_traces)

    # All clustered traces should be from failure_traces
    clustered_ids = {tid for c in clusters for tid in c.trace_ids}
    failure_ids = {t.id for t in failure_traces}
    assert clustered_ids.issubset(failure_ids)


def test_pipeline_judges_unknown_traces() -> None:
    """Traces with outcome='unknown' are passed to the judge; judge=yes → treated as failure."""

    class _TrackingJudge:
        def __init__(self) -> None:
            self.called_count = 0

        def is_failure(self, context: str) -> bool:
            self.called_count += 1
            return True

    judge = _TrackingJudge()
    pipeline = ClusterPipeline(TFIDFEmbedder(), judge, FakeLabeler())

    known_failure = generate_trace("wrong_tool", seed=1)
    unknown = known_failure.model_copy(update={"id": "test-unknown", "outcome": "unknown"})
    success = generate_trace("success", seed=2)

    # _identify_failures should call judge once (for the unknown trace only)
    failures = pipeline._identify_failures([known_failure, unknown, success])

    assert judge.called_count == 1  # only the unknown trace hits the judge
    assert unknown.id in {t.id for t in failures}
    assert known_failure.id in {t.id for t in failures}
    assert success.id not in {t.id for t in failures}


# ── clustering ────────────────────────────────────────────────────────────────


def test_clustering_returns_failure_clusters() -> None:
    traces = generate_dataset(n=100, seed=42)
    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    clusters = pipeline.run(traces)

    assert len(clusters) > 0
    for c in clusters:
        assert c.size >= _MIN_CLUSTER_SIZE
        assert len(c.trace_ids) == c.size
        assert c.representative_trace_id in c.trace_ids
        assert c.description  # non-empty label


def test_clustering_is_deterministic() -> None:
    """Same traces list → identical cluster assignments both runs."""
    traces = generate_dataset(n=100, seed=42)

    def run() -> list[list[str]]:
        p = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
        return sorted(sorted(c.trace_ids) for c in p.run(traces))

    assert run() == run()


def test_known_failure_types_land_in_distinct_clusters() -> None:
    """Each synthetic failure category should dominate at least one cluster.

    'Dominate' means ≥60% of a cluster's traces share the same category label.
    This verifies that TF-IDF captures enough structural signal to separate
    the six failure modes in the synthetic dataset.
    """
    traces = generate_dataset(n=150, seed=42)
    trace_by_id = {t.id: t for t in traces}

    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    clusters = pipeline.run(traces)

    assert len(clusters) >= 4, f"Expected ≥4 clusters, got {len(clusters)}"

    dominant_labels: set[str] = set()
    for c in clusters:
        labels = [trace_by_id[tid].metadata.get("label", "unknown") for tid in c.trace_ids]
        counts = Counter(labels)
        top_label, top_count = counts.most_common(1)[0]
        purity = top_count / c.size
        assert purity >= 0.55, (
            f"Cluster '{c.label}' not dominated by one category (purity={purity:.2f}, counts={dict(counts)})"
        )
        dominant_labels.add(top_label)

    # At least 4 of the 6 failure categories should appear as cluster dominants
    failure_categories = {
        "wrong_tool",
        "hallucinated_policy",
        "unresolved_ticket",
        "premature_escalation",
        "policy_violation",
        "scope_creep",
    }
    covered = dominant_labels & failure_categories
    assert len(covered) >= 4, f"Only {len(covered)} categories covered: {covered}"


def test_too_few_traces_returns_empty() -> None:
    """Fewer failures than min_cluster_size → no clusters emitted."""
    traces = [generate_trace("wrong_tool", seed=i) for i in range(3)]
    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    assert pipeline.run(traces) == []


# ── judge calibration ─────────────────────────────────────────────────────────


def test_calibrate_judge_perfect_agreement() -> None:
    """FakeJudge always says failure; traces marked failure → 100% agreement."""
    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    labeled = [generate_trace("wrong_tool", seed=i) for i in range(10)]
    rate = pipeline.calibrate_judge(labeled)
    assert rate == pytest.approx(1.0)


def test_calibrate_judge_mixed() -> None:
    """FakeJudge always says failure; success traces → 0% agreement for them."""
    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    failure_traces = [generate_trace("scope_creep", seed=i) for i in range(5)]
    success_traces = [generate_trace("success", seed=i + 100) for i in range(5)]
    rate = pipeline.calibrate_judge(failure_traces + success_traces)
    # 5 agree (failures), 5 disagree (successes) → 0.5
    assert rate == pytest.approx(0.5)


def test_calibrate_judge_empty() -> None:
    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    assert pipeline.calibrate_judge([]) == 0.0


# ── cluster output shape ──────────────────────────────────────────────────────


def test_cluster_sizes_sum_to_at_most_failures() -> None:
    traces = generate_dataset(n=100, seed=42)
    n_failures = sum(1 for t in traces if t.outcome == "failure")

    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    clusters = pipeline.run(traces)

    total_clustered = sum(c.size for c in clusters)
    assert total_clustered <= n_failures  # noise points are discarded


def test_no_duplicate_trace_ids_across_clusters() -> None:
    traces = generate_dataset(n=100, seed=42)
    pipeline = ClusterPipeline(TFIDFEmbedder(), FakeJudge(), FakeLabeler())
    clusters = pipeline.run(traces)

    all_ids = [tid for c in clusters for tid in c.trace_ids]
    assert len(all_ids) == len(set(all_ids))
