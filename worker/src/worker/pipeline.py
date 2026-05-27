"""Weekly optimization pipeline: ingest-check → cluster → optimize → PR-or-silence."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from core.clustering.pipeline import ClusterPipeline
from core.eval.harness import EvalHarness
from core.eval.runner import AgentConfig
from core.eval.split import split
from core.github.client import GitHubGateway
from core.github.publisher import PRPublisher
from core.optimizer.engine import Optimizer
from shared.models import EvalResult, FailureCluster, OptimizationRun, ProposedChange, Trace

from worker.digest import DigestNotifier, DigestPR, compose_weekly_digest
from worker.models import CustomerConfig, PipelineComponents, RunEvent
from worker.store import RunStore

logger = logging.getLogger(__name__)

# Minimum number of traces required to run the optimization pipeline.
# Below this threshold the clustering results are too sparse to be meaningful.
MIN_TRACES_FOR_OPTIMIZATION = 20


async def run_optimization_cycle(
    customer: CustomerConfig,
    traces: list[Trace],
    store: RunStore,
    gateway: GitHubGateway,
    components: PipelineComponents,
    digest_notifier: DigestNotifier | None = None,
) -> OptimizationRun:
    """Run one full optimization cycle for a customer.

    Stages (each isolated — a crash in one never corrupts the others):
      init        → create run record, check trace count
      clustering  → identify and label failure clusters
      optimization → GEPA mutations gated by eval harness
      publishing  → open GitHub PRs for survivors; silence if none

    The function always returns an OptimizationRun (status=completed|failed).
    It never raises — stage exceptions are caught, logged as RunEvents, and
    the run is marked failed. This ensures a bad optimization cycle can never
    open a PR.
    """
    run = OptimizationRun(
        organization_id=customer.organization_id,
        agent_id=customer.agent_id,
        status="running",
    )
    await store.create_run(run)
    await _emit(store, run.id, "init", "started", f"Optimization cycle started for agent {customer.agent_id}")

    # ── ingest-check ──────────────────────────────────────────────────────────
    if len(traces) < MIN_TRACES_FOR_OPTIMIZATION:
        await _emit(
            store,
            run.id,
            "init",
            "info",
            f"Not enough traces to optimize ({len(traces)} < {MIN_TRACES_FOR_OPTIMIZATION}). Skipping this cycle.",
            metadata={"trace_count": len(traces), "min_required": MIN_TRACES_FOR_OPTIMIZATION},
        )
        run = run.model_copy(update={"status": "completed"})
        await store.update_run(run)
        await _emit(store, run.id, "done", "completed", "Cycle skipped — insufficient traces.")
        await _send_weekly_digest(
            store,
            run,
            clusters=[],
            proposed_changes=[],
            eval_results=[],
            prs=[],
            digest_notifier=digest_notifier,
        )
        return run

    # ── clustering ────────────────────────────────────────────────────────────
    await _emit(
        store,
        run.id,
        "clustering",
        "started",
        f"Clustering {len(traces)} traces",
        metadata={"trace_count": len(traces)},
    )
    try:
        pipeline = ClusterPipeline(
            embedder=components.embedder,
            judge=components.clustering_judge,
            labeler=components.labeler,
        )
        clusters = pipeline.run(traces)
        run = run.model_copy(update={"cluster_ids": [c.id for c in clusters]})
        await store.update_run(run)
        await _emit(
            store,
            run.id,
            "clustering",
            "completed",
            f"Found {len(clusters)} failure cluster(s)",
            metadata={"cluster_count": len(clusters), "cluster_labels": [c.label for c in clusters]},
        )
    except Exception as exc:
        return await _fail(store, run, "clustering", exc)

    if not clusters:
        run = run.model_copy(update={"status": "completed"})
        await store.update_run(run)
        await _emit(store, run.id, "done", "completed", "No failure clusters — agent is performing well.")
        await _send_weekly_digest(
            store,
            run,
            clusters=[],
            proposed_changes=[],
            eval_results=[],
            prs=[],
            digest_notifier=digest_notifier,
        )
        return run

    # ── optimization ──────────────────────────────────────────────────────────
    await _emit(
        store,
        run.id,
        "optimization",
        "started",
        f"Optimizing {len(clusters)} cluster(s) (budget={components.mutation_budget})",
        metadata={"cluster_count": len(clusters)},
    )
    try:
        train, holdout = split(traces)

        harness = EvalHarness(
            runner=components.eval_runner,
            judge=components.eval_judge,
            seed_contexts=list(customer.seed_contexts),
            seed_labels=list(customer.seed_labels),
        )

        baseline = AgentConfig(
            prompt=customer.baseline_prompt,
            skills=customer.baseline_skills,
        )

        optimizer = Optimizer(
            mutator=components.mutator,
            harness=harness,
            budget=components.mutation_budget,
        )

        opt_result = optimizer.optimize(
            clusters=clusters,
            traces=traces,
            baseline=baseline,
            holdout=holdout,
            run_id=run.id,
        )

        # Persist eval results for health time series — every cycle, not just when PRs ship.
        eval_results_to_save = [
            er.model_copy(update={"optimization_run_id": run.id})
            for er in opt_result.eval_results
        ]
        if not eval_results_to_save:
            # Silent week: run baseline self-eval to anchor the time series.
            try:
                silent_report = harness.evaluate(baseline, baseline, holdout)
                eval_results_to_save.append(
                    EvalResult(
                        optimization_run_id=run.id,
                        baseline_score=silent_report.baseline_score,
                        candidate_score=silent_report.baseline_score,
                        delta=0.0,
                        p_value=1.0,
                        sample_size=silent_report.significance.sample_size,
                        passed=False,
                        judge_agreement_rate=silent_report.judge_agreement_rate,
                    )
                )
            except Exception as exc:
                logger.warning("Baseline self-eval failed (health time series will have a gap): %s", exc)

        for er in eval_results_to_save:
            await store.save_eval_result(er)

        run = run.model_copy(update={"proposed_change_ids": [c.id for c in opt_result.proposed_changes]})
        await store.update_run(run)
        await _emit(
            store,
            run.id,
            "optimization",
            "completed",
            f"{len(opt_result.proposed_changes)} candidate(s) passed the eval gate "
            f"({len(clusters) - len(opt_result.proposed_changes)} rejected)",
            metadata={
                "survivors": len(opt_result.proposed_changes),
                "rejected": len(clusters) - len(opt_result.proposed_changes),
                "holdout_size": len(holdout.cases),
            },
        )
    except Exception as exc:
        return await _fail(store, run, "optimization", exc)

    # ── publishing ────────────────────────────────────────────────────────────
    await _emit(
        store,
        run.id,
        "publishing",
        "started",
        f"Publishing {len(opt_result.proposed_changes)} change(s) to {customer.repo}",
    )
    try:
        publisher = PRPublisher(
            gateway=gateway,
            repo=customer.repo,
            config_path=customer.config_path,
            base_branch=customer.base_branch,
        )
        pub_result = publisher.publish(opt_result)

        pr_urls = [pr.url for pr in pub_result.opened]
        await _emit(
            store,
            run.id,
            "publishing",
            "completed",
            pub_result.silence_report or f"Opened {len(pub_result.opened)} PR(s)",
            metadata={
                "prs_opened": len(pub_result.opened),
                "prs_skipped_existing": pub_result.skipped_existing,
                "prs_skipped_gate": pub_result.skipped_failed_gate,
                "pr_urls": pr_urls,
                "silence": pub_result.silence_report,
            },
        )
    except Exception as exc:
        return await _fail(store, run, "publishing", exc)

    # ── done ──────────────────────────────────────────────────────────────────
    run = run.model_copy(update={"status": "completed"})
    await store.update_run(run)
    await _emit(store, run.id, "done", "completed", "Optimization cycle complete.")
    await _send_weekly_digest(
        store,
        run,
        clusters=clusters,
        proposed_changes=list(opt_result.proposed_changes),
        eval_results=eval_results_to_save,
        prs=[DigestPR(url=pr.url, title=pr.title, change_id=pr.change_id) for pr in pub_result.opened],
        digest_notifier=digest_notifier,
    )
    return run


# ── helpers ───────────────────────────────────────────────────────────────────


async def _emit(
    store: RunStore,
    run_id: str,
    stage: str,
    event: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    ev = RunEvent(
        run_id=run_id,
        stage=stage,  # type: ignore[arg-type]
        event=event,  # type: ignore[arg-type]
        message=message,
        metadata=metadata or {},
    )
    await store.log_event(ev)


async def _fail(
    store: RunStore,
    run: OptimizationRun,
    stage: str,
    exc: Exception,
) -> OptimizationRun:
    logger.exception("Stage '%s' failed for run %s", stage, run.id)
    run = run.model_copy(update={"status": "failed"})
    await store.update_run(run)
    await _emit(
        store,
        run.id,
        stage,
        "failed",
        f"Stage '{stage}' failed: {exc}",
        metadata={"error": str(exc), "error_type": type(exc).__name__},
    )
    return run


async def _send_weekly_digest(
    store: RunStore,
    run: OptimizationRun,
    *,
    clusters: list[FailureCluster],
    proposed_changes: list[ProposedChange],
    eval_results: list[EvalResult],
    prs: list[DigestPR],
    digest_notifier: DigestNotifier | None,
) -> None:
    existing = await store.get_weekly_digest_for_run(run.id)
    if existing is not None:
        return

    week_end = run.created_at
    week_start = week_end - timedelta(days=7)
    events = await store.list_events(run.id)
    previous_eval_results = await store.list_eval_results(
        run.agent_id, run.created_at, limit=25
    )
    alarms = await store.list_alarms(run.organization_id, run.agent_id, week_start, week_end)
    digest = compose_weekly_digest(
        run=run,
        events=events,
        clusters=clusters,
        proposed_changes=proposed_changes,
        eval_results=eval_results,
        previous_eval_results=previous_eval_results,
        alarms=alarms,
        prs=prs,
    )
    await store.save_weekly_digest(digest)
    if digest_notifier is not None:
        digest_notifier.send(digest)
