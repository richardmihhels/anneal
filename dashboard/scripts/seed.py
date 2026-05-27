"""Generate seed data for the Anneal dashboard.

Run from the repo root:
    python dashboard/scripts/seed.py

Writes dashboard/data/seed.json with 8 weeks of synthetic optimization runs.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parents[2]
for _pkg in ("shared/src", "core/src", "worker/src"):
    sys.path.insert(0, str(_ROOT / _pkg))

from core.clustering.embedder import TFIDFEmbedder  # noqa: E402
from core.clustering.judge import FakeJudge  # noqa: E402
from core.clustering.labeler import FakeLabeler  # noqa: E402
from core.clustering.pipeline import ClusterPipeline  # noqa: E402
from core.eval.harness import EvalHarness  # noqa: E402
from core.eval.runner import AgentConfig  # noqa: E402
from core.eval.split import split  # noqa: E402
from core.optimizer.engine import Optimizer  # noqa: E402
from core.optimizer.mutator import FakeMutator  # noqa: E402
from core.testing.generator import generate_dataset  # noqa: E402
from shared.models import (  # noqa: E402
    Alarm,
    EvalResult,
    OptimizationRun,
    Trace,  # noqa: E402
)
from worker.models import RunEvent  # noqa: E402


def _uid() -> str:
    return str(uuid.uuid4())


def _ts(days_ago: float) -> datetime:
    return datetime.now(UTC).replace(microsecond=0, second=0) - timedelta(days=days_ago)


def _ev(
    run_id: str,
    stage: str,
    event: str,
    message: str,
    ts: datetime,
    metadata: dict[str, Any] | None = None,
) -> RunEvent:
    return RunEvent(
        run_id=run_id,
        stage=stage,  # type: ignore[arg-type]
        event=event,  # type: ignore[arg-type]
        message=message,
        ts=ts,
        metadata=metadata or {},
    )


class _MutationAwareRunner:
    """Returns 'resolved' for mutation prompts, 'cannot help' for baseline."""

    def run(self, trace: Trace, config: AgentConfig) -> str:
        return "issue resolved successfully." if "mutation" in config.prompt else "I cannot help with that."


class _AlwaysPassRunner:
    """Both baseline and candidate succeed — delta=0, nothing ships."""

    def run(self, trace: Trace, config: AgentConfig) -> str:
        return "issue resolved successfully."


class _KeywordJudge:
    def score(self, context: str) -> float:
        return 1.0 if "resolved" in context.lower() else 0.0


_SEED_CONTEXTS = ["issue resolved successfully"] * 10 + ["I cannot help with that"] * 10
_SEED_LABELS = ["pass"] * 10 + ["fail"] * 10
_BASELINE = "anneal-baseline-v1"
_AGENT_ID = "cascade-support-v1"


def _good_components(runner: Any) -> tuple[Any, ...]:
    harness = EvalHarness(
        runner=runner,
        judge=_KeywordJudge(),
        seed_contexts=_SEED_CONTEXTS,
        seed_labels=_SEED_LABELS,
    )
    return harness, Optimizer(mutator=FakeMutator(), harness=harness, budget=1)


def run_good_cycle(seed: int, days_ago: float) -> dict[str, Any]:
    run_id = _uid()
    t0 = _ts(days_ago)

    traces = generate_dataset(n=150, seed=seed)
    _, holdout = split(traces)

    pipeline = ClusterPipeline(embedder=TFIDFEmbedder(), judge=FakeJudge(), labeler=FakeLabeler())
    clusters = pipeline.run(traces)

    _harness, optimizer = _good_components(_MutationAwareRunner())
    baseline = AgentConfig(prompt=_BASELINE, skills=())
    opt_result = optimizer.optimize(clusters, traces, baseline, holdout, run_id=run_id)

    survivors = len(opt_result.proposed_changes)
    rejected = len(clusters) - survivors

    run = OptimizationRun(
        id=run_id,
        agent_id=_AGENT_ID,
        created_at=t0,
        status="completed",
        cluster_ids=[c.id for c in clusters],
        proposed_change_ids=[c.id for c in opt_result.proposed_changes],
    )

    events = [
        _ev(run_id, "init", "started", f"Optimization cycle started for agent {_AGENT_ID}", t0),
        _ev(
            run_id,
            "clustering",
            "started",
            f"Clustering {len(traces)} traces",
            t0 + timedelta(seconds=1),
            {"trace_count": len(traces)},
        ),
        _ev(
            run_id,
            "clustering",
            "completed",
            f"Found {len(clusters)} failure cluster(s)",
            t0 + timedelta(seconds=8),
            {"cluster_count": len(clusters), "cluster_labels": [c.label for c in clusters]},
        ),
        _ev(
            run_id,
            "optimization",
            "started",
            f"Optimizing {len(clusters)} cluster(s) (budget=1)",
            t0 + timedelta(seconds=9),
            {"cluster_count": len(clusters)},
        ),
        _ev(
            run_id,
            "optimization",
            "completed",
            f"{survivors} candidate(s) passed the eval gate ({rejected} rejected)",
            t0 + timedelta(seconds=48),
            {"survivors": survivors, "rejected": rejected, "holdout_size": len(holdout.cases)},
        ),
        _ev(run_id, "publishing", "started", f"Publishing {survivors} change(s)", t0 + timedelta(seconds=49)),
        _ev(
            run_id,
            "publishing",
            "completed",
            f"Opened {survivors} PR(s)",
            t0 + timedelta(seconds=52),
            {"prs_opened": survivors, "silence": None},
        ),
        _ev(run_id, "done", "completed", "Optimization cycle complete.", t0 + timedelta(seconds=53)),
    ]

    # Attach optimization_run_id so the health view can group evals by run.
    eval_results_with_run = [
        er.model_copy(update={"optimization_run_id": run_id})
        for er in opt_result.eval_results
    ]

    return {
        "run": run,
        "events": events,
        "clusters": list(clusters),
        "proposed_changes": list(opt_result.proposed_changes),
        "eval_results": eval_results_with_run,
    }


def run_silent_cycle(seed: int, days_ago: float) -> dict[str, Any]:
    run_id = _uid()
    t0 = _ts(days_ago)

    traces = generate_dataset(n=150, seed=seed)
    _, holdout = split(traces)

    pipeline = ClusterPipeline(embedder=TFIDFEmbedder(), judge=FakeJudge(), labeler=FakeLabeler())
    clusters = pipeline.run(traces)

    _harness, optimizer = _good_components(_AlwaysPassRunner())
    baseline = AgentConfig(prompt=_BASELINE, skills=())
    optimizer.optimize(clusters, traces, baseline, holdout, run_id=run_id)

    n = len(clusters)
    silence_msg = (
        f"Anneal evaluated {n} failure cluster{'s' if n != 1 else ''} and found "
        f"no prompt change that beats the current baseline with statistical significance "
        f"(p < 0.05). Nothing shipped — which is the right call."
    )

    run = OptimizationRun(
        id=run_id,
        agent_id=_AGENT_ID,
        created_at=t0,
        status="completed",
        cluster_ids=[c.id for c in clusters],
        proposed_change_ids=[],
    )

    events = [
        _ev(run_id, "init", "started", f"Optimization cycle started for agent {_AGENT_ID}", t0),
        _ev(
            run_id,
            "clustering",
            "started",
            f"Clustering {len(traces)} traces",
            t0 + timedelta(seconds=1),
            {"trace_count": len(traces)},
        ),
        _ev(
            run_id,
            "clustering",
            "completed",
            f"Found {len(clusters)} failure cluster(s)",
            t0 + timedelta(seconds=8),
            {"cluster_count": len(clusters)},
        ),
        _ev(
            run_id,
            "optimization",
            "started",
            f"Optimizing {len(clusters)} cluster(s) (budget=1)",
            t0 + timedelta(seconds=9),
            {"cluster_count": len(clusters)},
        ),
        _ev(
            run_id,
            "optimization",
            "completed",
            f"0 candidate(s) passed the eval gate ({len(clusters)} rejected)",
            t0 + timedelta(seconds=44),
            {"survivors": 0, "rejected": len(clusters), "holdout_size": len(holdout.cases)},
        ),
        _ev(run_id, "publishing", "started", "Publishing 0 change(s)", t0 + timedelta(seconds=45)),
        _ev(
            run_id,
            "publishing",
            "completed",
            silence_msg,
            t0 + timedelta(seconds=46),
            {"prs_opened": 0, "silence": silence_msg},
        ),
        _ev(run_id, "done", "completed", "Optimization cycle complete.", t0 + timedelta(seconds=47)),
    ]

    # Persist a baseline self-eval so the health time series has a data point even in quiet weeks.
    harness_baseline, _ = _good_components(_AlwaysPassRunner())
    silent_report = harness_baseline.evaluate(baseline, baseline, holdout)
    baseline_eval = EvalResult(
        optimization_run_id=run_id,
        proposed_change_id=None,
        baseline_score=silent_report.baseline_score,
        candidate_score=silent_report.baseline_score,
        delta=0.0,
        p_value=1.0,
        sample_size=silent_report.significance.sample_size,
        passed=False,
        judge_agreement_rate=silent_report.judge_agreement_rate,
    )

    return {
        "run": run,
        "events": events,
        "clusters": list(clusters),
        "proposed_changes": [],
        "eval_results": [baseline_eval],
    }


def run_failed_cycle(days_ago: float) -> dict[str, Any]:
    run_id = _uid()
    t0 = _ts(days_ago)

    run = OptimizationRun(
        id=run_id,
        agent_id=_AGENT_ID,
        created_at=t0,
        status="failed",
        cluster_ids=[],
        proposed_change_ids=[],
    )

    exc_msg = "embedder unavailable: connection refused to embedding service"
    events = [
        _ev(run_id, "init", "started", f"Optimization cycle started for agent {_AGENT_ID}", t0),
        _ev(
            run_id,
            "clustering",
            "started",
            "Clustering 150 traces",
            t0 + timedelta(seconds=1),
            {"trace_count": 150},
        ),
        _ev(
            run_id,
            "clustering",
            "failed",
            f"Stage 'clustering' failed: {exc_msg}",
            t0 + timedelta(seconds=4),
            {"error": exc_msg, "error_type": "RuntimeError"},
        ),
    ]

    return {"run": run, "events": events, "clusters": [], "proposed_changes": [], "eval_results": []}


def run_skipped_cycle(days_ago: float) -> dict[str, Any]:
    run_id = _uid()
    t0 = _ts(days_ago)

    trace_count = 8
    run = OptimizationRun(
        id=run_id,
        agent_id=_AGENT_ID,
        created_at=t0,
        status="completed",
        cluster_ids=[],
        proposed_change_ids=[],
    )

    events = [
        _ev(run_id, "init", "started", f"Optimization cycle started for agent {_AGENT_ID}", t0),
        _ev(
            run_id,
            "init",
            "info",
            f"Not enough traces to optimize ({trace_count} < 20). Skipping this cycle.",
            t0 + timedelta(milliseconds=200),
            {"trace_count": trace_count, "min_required": 20},
        ),
        _ev(run_id, "done", "completed", "Cycle skipped — insufficient traces.", t0 + timedelta(milliseconds=400)),
    ]

    return {"run": run, "events": events, "clusters": [], "proposed_changes": [], "eval_results": []}


def _serialize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _serialize(dataclasses.asdict(obj))
    if hasattr(obj, "model_dump"):
        return _serialize(obj.model_dump(mode="json"))
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _make_alarms() -> list[Alarm]:
    """Two sample alarms on the cascade-support-v1 agent."""
    return [
        Alarm(
            agent_id="cascade-support-v1",
            organization_id="org_demo",
            category="policy_violation",
            baseline_rate=0.06,
            current_rate=0.28,
            window_hours=24,
            affected_trace_count=14,
            first_detected=_ts(0.4),
            cause_hypothesis=(
                "Hypothesis (AI-generated — treat as a guess): The 'policy_violation' "
                "failure rate rose 367% from 6.0% to 28.0%. This may indicate a recent "
                "change in user behaviour — a higher proportion of requests are asking "
                "for partial refunds, which the agent is incorrectly granting."
            ),
            notified=True,
        ),
    ]


def main() -> None:
    scenarios = [
        ("good", 42, 1.0),
        ("silent", 17, 8.0),
        ("good", 7, 15.0),
        ("failed", None, 22.0),
        ("good", 13, 29.0),
        ("silent", 99, 36.0),
        ("good", 55, 43.0),
        ("skipped", None, 50.0),
    ]

    all_runs, all_events, all_clusters, all_changes, all_evals = [], [], [], [], []

    for kind, seed, days_ago in scenarios:
        print(f"  {kind:<8} seed={str(seed):<4} days_ago={days_ago}")
        if kind == "good":
            r = run_good_cycle(seed=seed, days_ago=days_ago)
        elif kind == "silent":
            r = run_silent_cycle(seed=seed, days_ago=days_ago)
        elif kind == "failed":
            r = run_failed_cycle(days_ago=days_ago)
        else:
            r = run_skipped_cycle(days_ago=days_ago)

        all_runs.append(r["run"])
        all_events.extend(r["events"])
        all_clusters.extend(r["clusters"])
        all_changes.extend(r["proposed_changes"])
        all_evals.extend(r["eval_results"])

    data = _serialize(
        {
            "runs": all_runs,
            "events": all_events,
            "clusters": all_clusters,
            "proposed_changes": all_changes,
            "eval_results": all_evals,
            "alarms": _make_alarms(),
        }
    )

    out = Path(__file__).parents[1] / "data" / "seed.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, indent=2))

    print(f"\nWrote {out}")
    print(f"  {len(all_runs)} runs  {len(all_events)} events  {len(all_clusters)} clusters")
    print(f"  {len(all_changes)} proposed_changes  {len(all_evals)} eval_results")


if __name__ == "__main__":
    main()
