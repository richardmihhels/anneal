"""Tests for GitHub App integration: PR body, silence path, idempotency."""

from __future__ import annotations

import pytest
from core.github import (
    FakeGitHubGateway,
    PRPublisher,
    build_pr_body,
    build_pr_title,
    build_silence_report,
    idempotency_key,
    pr_label,
)
from core.github.pr import _extract_cluster_description, _extract_failure_excerpt
from core.optimizer.engine import OptimizationResult
from shared.models import EvalResult, ProposedChange

# ── fixtures ──────────────────────────────────────────────────────────────────

_RATIONALE = """\
Target failure: Wrong tool routed to order lookup (8 cases in cluster 'cluster-0')

Representative failure:
> USER: Does Cascade support SSO? TOOLS: lookup_order RESPONSE: You're on Pro.

Prompt change:
  Before: You are a helpful customer support agent.
  After:  You are a helpful customer support agent. Use search_kb for product questions.

Eval result (holdout n=40):
  Baseline score : 0.250
  Candidate score: 0.800
  Improvement    : +0.550
  p-value        : 0.0001
  Judge agreement: 95.0%
"""


def _make_change(
    *,
    before: str = "You are a helpful customer support agent.",
    after: str = "You are a helpful customer support agent. Use search_kb for product questions.",
    rationale: str = _RATIONALE,
    run_id: str = "run-1",
) -> ProposedChange:
    return ProposedChange(
        optimization_run_id=run_id,
        target="system_prompt",
        before=before,
        after=after,
        rationale=rationale,
    )


def _make_eval(
    *,
    change_id: str,
    passed: bool = True,
    delta: float = 0.55,
    p_value: float = 0.0001,
    sample_size: int = 40,
    baseline_score: float = 0.25,
    candidate_score: float = 0.80,
    judge_agreement_rate: float = 0.95,
) -> EvalResult:
    return EvalResult(
        proposed_change_id=change_id,
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        delta=delta,
        p_value=p_value,
        sample_size=sample_size,
        passed=passed,
        judge_agreement_rate=judge_agreement_rate,
    )


def _make_result(
    change: ProposedChange | None = None,
    ev: EvalResult | None = None,
) -> OptimizationResult:
    if change is None:
        change = _make_change()
    if ev is None:
        ev = _make_eval(change_id=change.id)
    return OptimizationResult(
        proposed_changes=(change,),
        eval_results=(ev,),
    )


# ── rationale parser ──────────────────────────────────────────────────────────


def test_extract_cluster_description() -> None:
    desc = _extract_cluster_description(_RATIONALE)
    assert desc == "Wrong tool routed to order lookup"


def test_extract_cluster_description_missing() -> None:
    assert _extract_cluster_description("no target here") == "unknown failure pattern"


def test_extract_failure_excerpt() -> None:
    excerpt = _extract_failure_excerpt(_RATIONALE)
    assert "Does Cascade support SSO?" in excerpt
    assert excerpt.startswith("USER:")


def test_extract_failure_excerpt_missing() -> None:
    assert _extract_failure_excerpt("no excerpt here") == ""


# ── idempotency key ───────────────────────────────────────────────────────────


def test_idempotency_key_stable_across_runs() -> None:
    c1 = _make_change(run_id="run-1")
    c2 = _make_change(run_id="run-2")  # same content, different run
    assert idempotency_key(c1) == idempotency_key(c2)


def test_idempotency_key_changes_with_before() -> None:
    c1 = _make_change(before="prompt v1")
    c2 = _make_change(before="prompt v2")
    assert idempotency_key(c1) != idempotency_key(c2)


def test_pr_label_format() -> None:
    change = _make_change()
    label = pr_label(change)
    assert label.startswith("anneal:")
    assert len(label) == len("anneal:") + 12


# ── PR body format ────────────────────────────────────────────────────────────


def test_pr_title_contains_description_and_delta() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id, delta=0.55, sample_size=40)
    title = build_pr_title(change, ev)
    assert "Wrong tool routed to order lookup" in title
    assert "+55%" in title
    assert "n=40" in title


def test_pr_title_within_length_limit() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    title = build_pr_title(change, ev)
    assert len(title) <= 80  # generous allowance, description itself is ≤72


def test_pr_title_truncates_long_description() -> None:
    long_rationale = _RATIONALE.replace(
        "Wrong tool routed to order lookup",
        "A" * 100,
    )
    change = _make_change(rationale=long_rationale)
    ev = _make_eval(change_id=change.id)
    title = build_pr_title(change, ev)
    assert "…" in title
    assert len(title) <= 90


def test_pr_body_one_line_summary() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    body = build_pr_body(change, ev)
    # First non-empty line is the summary
    first_line = next(line for line in body.splitlines() if line.strip())
    assert "Wrong tool routed to order lookup" in first_line


def test_pr_body_contains_before_after() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    body = build_pr_body(change, ev)
    assert change.before in body
    assert change.after in body
    assert "# Before" in body
    assert "# After" in body


def test_pr_body_contains_failure_excerpt() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    body = build_pr_body(change, ev)
    assert "Does Cascade support SSO?" in body


def test_pr_body_contains_eval_stats() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id, delta=0.55, p_value=0.0001, sample_size=40)
    body = build_pr_body(change, ev)
    assert "40" in body  # sample size
    assert "0.000" in body  # p-value
    assert "+55%" in body


def test_pr_body_contains_do_not_merge_guard() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    body = build_pr_body(change, ev)
    assert "Do not merge if" in body


def test_pr_body_not_wall_of_text() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    body = build_pr_body(change, ev)
    # Prompt content can be long, but the structural text should be concise
    lines = [line for line in body.splitlines() if line.strip()]
    assert len(lines) <= 30, f"PR body has {len(lines)} non-empty lines — too verbose"


# ── silence report ────────────────────────────────────────────────────────────


def test_silence_report_positive_when_no_clusters() -> None:
    msg = build_silence_report(0)
    assert "well" in msg.lower() or "no failure" in msg.lower()


def test_silence_report_positive_when_clusters_found_but_none_pass() -> None:
    msg = build_silence_report(3)
    assert "3" in msg
    assert "nothing shipped" in msg.lower() or "nothing" in msg.lower()
    assert "regression" not in msg.lower() or "no regression" in msg.lower()


def test_silence_report_never_negative() -> None:
    for n in [0, 1, 5, 20]:
        msg = build_silence_report(n)
        assert "error" not in msg.lower()
        assert "failed" not in msg.lower()
        assert "no clusters" not in msg.lower() or n == 0


# ── publisher: normal path ────────────────────────────────────────────────────


def _make_publisher(
    gw: FakeGitHubGateway,
    repo: str = "acme/agent",
    config_path: str = "agent/config.py",
) -> PRPublisher:
    return PRPublisher(gateway=gw, repo=repo, config_path=config_path, base_branch="main")


def test_publisher_opens_pr_for_passing_change() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    result = _make_result(change, ev)

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)

    pub = _make_publisher(gw)
    pub_result = pub.publish(result)

    assert len(pub_result.opened) == 1
    assert pub_result.skipped_existing == 0
    assert pub_result.skipped_failed_gate == 0
    assert pub_result.silence_report is None
    assert "acme/agent/pull/1" in pub_result.opened[0].url


def test_publisher_pr_body_is_in_opened_pr() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    result = _make_result(change, ev)

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)

    pub = _make_publisher(gw)
    pub.publish(result)

    pr = gw.opened_prs[0]
    assert "Do not merge if" in pr["body"]
    assert "What changed" in pr["body"]


# ── publisher: hard gate ──────────────────────────────────────────────────────


def test_hard_gate_rejects_non_passing_change() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id, passed=False, delta=-0.1, p_value=0.9)
    result = OptimizationResult(
        proposed_changes=(change,),
        eval_results=(ev,),
    )

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)

    pub = _make_publisher(gw)
    pub_result = pub.publish(result)

    assert pub_result.opened == ()
    assert pub_result.skipped_failed_gate == 1
    assert gw.opened_prs == []


def test_hard_gate_rejects_zero_delta() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id, passed=False, delta=0.0, p_value=1.0)
    result = OptimizationResult(proposed_changes=(change,), eval_results=(ev,))

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)

    pub = _make_publisher(gw)
    pub_result = pub.publish(result)

    assert pub_result.opened == ()
    assert gw.opened_prs == []


def test_hard_gate_rechecks_inconsistent_passed_flag() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id, passed=True, delta=0.1, p_value=0.5)
    result = OptimizationResult(proposed_changes=(change,), eval_results=(ev,))
    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)

    published = _make_publisher(gw).publish(result)

    assert published.opened == ()
    assert published.skipped_failed_gate == 1


def test_publisher_rejects_unpaired_changes() -> None:
    change = _make_change()
    result = OptimizationResult(proposed_changes=(change,), eval_results=())

    with pytest.raises(ValueError, match="exactly one eval"):
        _make_publisher(FakeGitHubGateway()).publish(result)


# ── publisher: idempotency ────────────────────────────────────────────────────


def test_idempotency_no_duplicate_pr() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    result = _make_result(change, ev)

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)
    pub = _make_publisher(gw)

    first = pub.publish(result)
    assert len(first.opened) == 1

    # Second publish with same changes — PR already exists
    second = pub.publish(result)
    assert second.opened == ()
    assert second.skipped_existing == 1
    assert len(gw.opened_prs) == 1  # still only one PR


def test_idempotency_different_run_same_cluster_no_dup() -> None:
    """Same cluster + same baseline in a second weekly run → skip, not duplicate."""
    change_run1 = _make_change(run_id="run-week-1")
    change_run2 = _make_change(run_id="run-week-2")  # same content, new run

    ev1 = _make_eval(change_id=change_run1.id)
    ev2 = _make_eval(change_id=change_run2.id)

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change_run1.before)
    pub = _make_publisher(gw)

    r1 = pub.publish(OptimizationResult(proposed_changes=(change_run1,), eval_results=(ev1,)))
    assert len(r1.opened) == 1

    r2 = pub.publish(OptimizationResult(proposed_changes=(change_run2,), eval_results=(ev2,)))
    assert r2.skipped_existing == 1
    assert len(gw.opened_prs) == 1


def test_idempotency_different_before_opens_new_pr() -> None:
    """If baseline prompt changed, the cluster is a new situation — open a new PR."""
    change_v1 = _make_change(before="prompt v1", after="improved prompt v1")
    change_v2 = _make_change(before="prompt v2", after="improved prompt v2")  # different before

    ev1 = _make_eval(change_id=change_v1.id)
    ev2 = _make_eval(change_id=change_v2.id)

    gw = FakeGitHubGateway()
    pub = _make_publisher(gw)

    gw.add_file("acme/agent", "agent/config.py", "prompt v1")
    r1 = pub.publish(OptimizationResult(proposed_changes=(change_v1,), eval_results=(ev1,)))
    assert len(r1.opened) == 1

    gw.add_file("acme/agent", "agent/config.py", "prompt v2")
    r2 = pub.publish(OptimizationResult(proposed_changes=(change_v2,), eval_results=(ev2,)))
    assert len(r2.opened) == 1  # new PR because baseline changed
    assert len(gw.opened_prs) == 2


# ── publisher: silence path ───────────────────────────────────────────────────


def test_silence_path_empty_result() -> None:
    """No proposed changes at all → silence report emitted."""
    result = OptimizationResult(proposed_changes=(), eval_results=())

    gw = FakeGitHubGateway()
    pub = _make_publisher(gw)
    pub_result = pub.publish(result)

    assert pub_result.opened == ()
    assert pub_result.silence_report is not None
    assert "nothing" in pub_result.silence_report.lower() or "no" in pub_result.silence_report.lower()


def test_silence_path_all_gated_out() -> None:
    """All changes fail the hard gate → silence report, not an error."""
    change = _make_change()
    ev = _make_eval(change_id=change.id, passed=False, delta=-0.2, p_value=0.9)
    result = OptimizationResult(proposed_changes=(change,), eval_results=(ev,))

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)
    pub = _make_publisher(gw)
    pub_result = pub.publish(result)

    assert pub_result.opened == ()
    assert pub_result.silence_report is not None


def test_silence_path_not_emitted_when_pr_already_exists() -> None:
    """If a PR already existed (skipped_existing > 0), silence_report should be None."""
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    result = _make_result(change, ev)

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)
    pub = _make_publisher(gw)

    pub.publish(result)  # opens PR
    second = pub.publish(result)  # skips (existing PR)

    assert second.skipped_existing == 1
    assert second.silence_report is None  # not silent — a PR already covers it


# ── publisher: patch not found ────────────────────────────────────────────────


def test_patch_not_found_fails_closed() -> None:
    """A stale target fails the run path without opening a PR."""
    change = _make_change(before="this text is not in the file")
    ev = _make_eval(change_id=change.id)
    result = _make_result(change, ev)

    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", "completely different content")
    pub = _make_publisher(gw)
    with pytest.raises(ValueError, match="not found verbatim"):
        pub.publish(result)

    assert gw.opened_prs == []


def test_config_file_not_found_fails_closed() -> None:
    """A missing configured target is an operational failure, not a silent week."""
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    result = _make_result(change, ev)

    gw = FakeGitHubGateway()  # no file added
    pub = _make_publisher(gw)
    with pytest.raises(FileNotFoundError):
        pub.publish(result)

    assert gw.opened_prs == []


def test_github_write_failure_propagates_without_pr() -> None:
    change = _make_change()
    ev = _make_eval(change_id=change.id)
    result = _make_result(change, ev)

    class _WriteFailureGateway(FakeGitHubGateway):
        def update_file(
            self,
            repo: str,
            path: str,
            content: str,
            sha: str,
            branch: str,
            message: str,
        ) -> None:
            raise RuntimeError("GitHub write unavailable")

    gw = _WriteFailureGateway()
    gw.add_file("acme/agent", "agent/config.py", change.before)

    with pytest.raises(RuntimeError, match="GitHub write unavailable"):
        _make_publisher(gw).publish(result)

    assert gw.opened_prs == []


# ── publisher: multiple changes ───────────────────────────────────────────────


def test_multiple_changes_publish_only_strongest() -> None:
    before_a = "prompt for cluster A"
    before_b = "prompt for cluster B"

    rationale_a = _RATIONALE.replace("Wrong tool routed to order lookup", "Cluster A failure")
    rationale_b = _RATIONALE.replace("Wrong tool routed to order lookup", "Cluster B failure")

    change_a = _make_change(before=before_a, after="improved A", rationale=rationale_a)
    change_b = _make_change(before=before_b, after="improved B", rationale=rationale_b)
    ev_a = _make_eval(change_id=change_a.id, delta=0.20)
    ev_b = _make_eval(change_id=change_b.id, delta=0.60)

    # Both prompts are in the same config file
    gw = FakeGitHubGateway()
    gw.add_file("acme/agent", "agent/config.py", f"{before_a}\n{before_b}")
    pub = _make_publisher(gw)

    result = OptimizationResult(
        proposed_changes=(change_a, change_b),
        eval_results=(ev_a, ev_b),
    )
    pub_result = pub.publish(result)

    assert len(pub_result.opened) == 1
    assert pub_result.opened[0].change_id == change_b.id
    assert len(gw.opened_prs) == 1
