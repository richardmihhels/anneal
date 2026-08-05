"""Tests for the eval harness: significance math, leakage prevention, judge calibration."""

from __future__ import annotations

import pytest
from core.eval import (
    MIN_JUDGE_AGREEMENT,
    AgentConfig,
    EvalHarness,
    FakeAgentRunner,
    FakeEvalJudge,
    JudgeCalibrationError,
    calibrate,
    paired_t_test,
    split,
)
from core.eval.split import _TOKEN, HoldoutSet
from core.testing.generator import generate_dataset, generate_trace

# ── split / leakage prevention ────────────────────────────────────────────────


def test_holdout_direct_construction_raises() -> None:
    """HoldoutSet cannot be constructed without the module-private token."""
    from core.eval.split import EvalCase

    trace = generate_trace("wrong_tool", seed=0)
    case = EvalCase(trace=trace, human_label="fail")
    with pytest.raises(RuntimeError, match="eval.split()"):
        HoldoutSet(cases=(case,))


def test_holdout_direct_construction_wrong_token_raises() -> None:
    from core.eval.split import EvalCase

    trace = generate_trace("wrong_tool", seed=0)
    case = EvalCase(trace=trace, human_label="fail")
    with pytest.raises(RuntimeError):
        HoldoutSet(cases=(case,), _token=object())


def test_split_uses_correct_token() -> None:
    """split() produces a valid HoldoutSet (token check passes)."""
    traces = generate_dataset(n=50, seed=42)
    _, holdout = split(traces, seed=42)
    assert isinstance(holdout, HoldoutSet)
    assert holdout._token is _TOKEN


def test_split_fraction_near_20_percent() -> None:
    traces = generate_dataset(n=200, seed=42)
    train, holdout = split(traces, seed=42)
    total = len(train.cases) + len(holdout.cases)
    assert total == len(traces)
    holdout_frac = len(holdout.cases) / total
    assert 0.10 <= holdout_frac <= 0.30, f"Unexpected holdout fraction: {holdout_frac:.2f}"


def test_split_is_deterministic() -> None:
    traces = generate_dataset(n=100, seed=42)
    _, h1 = split(traces, seed=42)
    _, h2 = split(traces, seed=42)
    assert {c.trace.id for c in h1.cases} == {c.trace.id for c in h2.cases}


def test_split_different_seeds_differ() -> None:
    traces = generate_dataset(n=100, seed=42)
    _, h1 = split(traces, seed=1)
    _, h2 = split(traces, seed=2)
    # Highly unlikely that both seeds produce identical assignments over 100 traces
    assert {c.trace.id for c in h1.cases} != {c.trace.id for c in h2.cases}


def test_split_no_overlap() -> None:
    traces = generate_dataset(n=100, seed=42)
    train, holdout = split(traces, seed=42)
    train_ids = {c.trace.id for c in train.cases}
    holdout_ids = {c.trace.id for c in holdout.cases}
    assert train_ids.isdisjoint(holdout_ids)


# ── significance math ─────────────────────────────────────────────────────────


def test_paired_t_test_significant_improvement() -> None:
    baseline = [0.0] * 30
    candidate = [1.0] * 30
    result = paired_t_test(baseline, candidate)
    assert result.passed is True
    assert result.delta == pytest.approx(1.0)
    assert result.p_value < 0.001


def test_paired_t_test_no_improvement() -> None:
    scores = [0.5] * 30
    result = paired_t_test(scores, scores)
    assert result.passed is False
    assert result.delta == pytest.approx(0.0)
    assert result.p_value == pytest.approx(1.0)


def test_paired_t_test_regression_not_significant() -> None:
    """If candidate is worse than baseline, test should not pass."""
    baseline = [1.0] * 30
    candidate = [0.0] * 30
    result = paired_t_test(baseline, candidate)
    assert result.passed is False
    assert result.delta < 0
    assert result.p_value == pytest.approx(1.0)


def test_paired_t_test_small_delta_not_significant() -> None:
    """High variance, tiny mean delta → t-test should not reach significance."""
    import random

    rng = random.Random(0)
    # Large noise swamps the tiny mean shift; paired differences are not constant
    baseline = [rng.gauss(0.5, 0.4) for _ in range(10)]
    candidate = [b + rng.gauss(0.005, 0.4) for b in baseline]
    result = paired_t_test(baseline, candidate)
    assert result.passed is False


def test_paired_t_test_too_few_samples() -> None:
    result = paired_t_test([1.0], [0.5])
    assert result.passed is False
    assert result.p_value == pytest.approx(1.0)


def test_paired_t_test_rejects_small_perfect_sample() -> None:
    result = paired_t_test([0.0] * 9, [1.0] * 9)
    assert result.delta == pytest.approx(1.0)
    assert result.sample_size == 9
    assert result.passed is False
    assert result.p_value == pytest.approx(1.0)


def test_paired_t_test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="same length"):
        paired_t_test([1.0, 0.5], [1.0])


def test_paired_t_test_sample_size() -> None:
    b = [0.0] * 25
    c = [1.0] * 25
    result = paired_t_test(b, c)
    assert result.sample_size == 25


# ── judge calibration ─────────────────────────────────────────────────────────


def test_calibrate_perfect_agreement() -> None:
    """FakeEvalJudge(1.0) always predicts 'pass'; all-pass labels → 100% agreement."""
    judge = FakeEvalJudge(default_score=1.0)
    contexts = ["ctx1", "ctx2", "ctx3"]
    labels = ["pass", "pass", "pass"]
    rate = calibrate(judge, contexts, labels)
    assert rate == pytest.approx(1.0)


def test_calibrate_zero_agreement_raises() -> None:
    """Judge always predicts 'pass' but all labels are 'fail' → 0% → raises."""
    judge = FakeEvalJudge(default_score=1.0)
    contexts = ["ctx1", "ctx2", "ctx3"]
    labels = ["fail", "fail", "fail"]
    with pytest.raises(JudgeCalibrationError, match="below the required threshold"):
        calibrate(judge, contexts, labels)


def test_calibrate_below_threshold_raises() -> None:
    """Agreement just below MIN_JUDGE_AGREEMENT should raise."""
    judge = FakeEvalJudge(default_score=1.0)
    n = 100
    fail_count = int(n * (1 - MIN_JUDGE_AGREEMENT + 0.01))
    labels = ["pass"] * (n - fail_count) + ["fail"] * fail_count
    contexts = [f"ctx{i}" for i in range(n)]
    with pytest.raises(JudgeCalibrationError):
        calibrate(judge, contexts, labels)


def test_calibrate_at_threshold_passes() -> None:
    """Agreement exactly at MIN_JUDGE_AGREEMENT should not raise."""
    judge = FakeEvalJudge(default_score=1.0)
    n = 100
    pass_count = int(n * MIN_JUDGE_AGREEMENT)
    labels = ["pass"] * pass_count + ["fail"] * (n - pass_count)
    contexts = [f"ctx{i}" for i in range(n)]
    rate = calibrate(judge, contexts, labels)
    assert rate >= MIN_JUDGE_AGREEMENT


def test_calibrate_empty_raises() -> None:
    judge = FakeEvalJudge()
    with pytest.raises(ValueError, match="empty"):
        calibrate(judge, [], [])


def test_calibrate_length_mismatch_raises() -> None:
    judge = FakeEvalJudge()
    with pytest.raises(ValueError, match="same length"):
        calibrate(judge, ["ctx"], ["pass", "fail"])


# ── harness end-to-end ────────────────────────────────────────────────────────


def test_harness_candidate_better_than_baseline() -> None:
    traces = generate_dataset(n=100, seed=42)
    _, holdout = split(traces, seed=42)

    assert holdout.cases, "Need at least one holdout case"

    class _PairedRunner:
        def __init__(self, baseline_rate: float, candidate_rate: float) -> None:
            self._b = FakeAgentRunner(pass_rate=baseline_rate)
            self._c = FakeAgentRunner(pass_rate=candidate_rate)
            self.baseline_config = AgentConfig(prompt="baseline", skills=())
            self.candidate_config = AgentConfig(prompt="candidate", skills=())

        def run(self, trace: object, config: AgentConfig) -> str:
            if config is self.baseline_config:
                return self._b.run(trace, config)  # type: ignore[arg-type]
            return self._c.run(trace, config)  # type: ignore[arg-type]

    class _ContentJudge:
        """Returns 1.0 if 'resolved' in the response, 0.0 otherwise."""

        def score(self, context: str) -> float:
            return 1.0 if "resolved" in context.lower() else 0.0

    paired = _PairedRunner(0.0, 1.0)
    content_judge = _ContentJudge()
    # Calibrate: FakeAgentRunner(pass_rate=1.0) always returns "resolved" → 1.0
    # seed_labels are all "pass" → judge_pass=True matches → 100% agreement
    harness = EvalHarness(
        runner=paired,  # type: ignore[arg-type]
        judge=content_judge,  # type: ignore[arg-type]
        seed_contexts=["resolved successfully"] * len(holdout.cases),
        seed_labels=["pass"] * len(holdout.cases),
    )

    report = harness.evaluate(paired.baseline_config, paired.candidate_config, holdout)
    assert report.passed is True
    assert report.candidate_score > report.baseline_score
    assert report.judge_agreement_rate >= MIN_JUDGE_AGREEMENT


def test_harness_miscalibrated_judge_raises() -> None:
    """A judge that disagrees with all human labels should raise JudgeCalibrationError."""
    traces = generate_dataset(n=50, seed=42)
    _, holdout = split(traces, seed=42)
    assert holdout.cases

    # All holdout labels are "pass" or "fail"; FakeEvalJudge(1.0) always says pass.
    # Force all labels to "fail" so agreement is 0%.
    from core.eval.split import EvalCase

    bad_cases = tuple(EvalCase(trace=c.trace, human_label="fail") for c in holdout.cases)
    bad_holdout = HoldoutSet(cases=bad_cases, _token=_TOKEN)

    seed_contexts = [c.trace.id for c in bad_holdout.cases]
    seed_labels = [c.human_label for c in bad_holdout.cases]

    harness = EvalHarness(
        runner=FakeAgentRunner(pass_rate=0.5),  # type: ignore[arg-type]
        judge=FakeEvalJudge(default_score=1.0),  # always says pass → disagrees with all "fail" labels
        seed_contexts=seed_contexts,
        seed_labels=seed_labels,
    )

    baseline = AgentConfig(prompt="b", skills=())
    candidate = AgentConfig(prompt="c", skills=())

    with pytest.raises(JudgeCalibrationError):
        harness.evaluate(baseline, candidate, bad_holdout)


def test_harness_empty_holdout_returns_no_improvement() -> None:
    """If holdout is empty, no cases to score → significance defaults to no-pass."""
    harness = EvalHarness(
        runner=FakeAgentRunner(),  # type: ignore[arg-type]
        judge=FakeEvalJudge(default_score=1.0),
        seed_contexts=["ctx1"],
        seed_labels=["pass"],
    )
    empty_holdout = HoldoutSet(cases=(), _token=_TOKEN)
    baseline = AgentConfig(prompt="b", skills=())
    candidate = AgentConfig(prompt="c", skills=())

    report = harness.evaluate(baseline, candidate, empty_holdout)
    assert report.passed is False
    assert report.significance.sample_size == 0
