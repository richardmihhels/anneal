"""Tests for the synthetic trace generator."""

from __future__ import annotations

import pytest
from core.testing.generator import (
    FailureCategory,
    generate_dataset,
    generate_trace,
)
from shared.models import Trace

ALL_CATEGORIES: list[FailureCategory] = [
    "success",
    "wrong_tool",
    "hallucinated_policy",
    "unresolved_ticket",
    "premature_escalation",
    "policy_violation",
    "scope_creep",
]


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_generate_trace_is_valid(category: FailureCategory) -> None:
    trace = generate_trace(category, seed=0)
    assert isinstance(trace, Trace)
    assert trace.agent_id == "cascade-support-v1"
    assert len(trace.spans) >= 2
    assert trace.metadata["label"] == category


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_outcome_matches_category(category: FailureCategory) -> None:
    trace = generate_trace(category, seed=1)
    if category == "success":
        assert trace.outcome == "success"
    else:
        assert trace.outcome == "failure"
        assert trace.metadata["failure_category"] == category


def test_spans_have_consistent_trace_id() -> None:
    trace = generate_trace("wrong_tool", seed=2)
    for span in trace.spans:
        assert span.trace_id == trace.id


def test_spans_are_chronological() -> None:
    trace = generate_trace("policy_violation", seed=3)
    times = [s.start_time for s in trace.spans]
    assert times == sorted(times)


def test_span_durations_are_positive() -> None:
    trace = generate_trace("scope_creep", seed=4)
    for span in trace.spans:
        assert span.duration_ms >= 0


def test_generate_dataset_returns_n_traces() -> None:
    traces = generate_dataset(n=20, seed=99)
    assert len(traces) == 20
    assert all(isinstance(t, Trace) for t in traces)


def test_dataset_covers_all_categories() -> None:
    traces = generate_dataset(n=200, seed=42)
    found = {t.metadata["label"] for t in traces}
    assert found == set(ALL_CATEGORIES)


def test_generate_trace_is_deterministic() -> None:
    t1 = generate_trace("hallucinated_policy", seed=7)
    t2 = generate_trace("hallucinated_policy", seed=7)
    # IDs are random but structure should be the same category/outcome
    assert t1.outcome == t2.outcome
    assert len(t1.spans) == len(t2.spans)
