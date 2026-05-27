from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from shared.models import EvalResult, FailureCluster, ProposedChange, Trace

from core.clustering.context import extract_context
from core.eval.harness import EvalHarness, EvalReport
from core.eval.runner import AgentConfig
from core.eval.scoring import JudgeCalibrationError
from core.eval.split import HoldoutSet
from core.optimizer.mutator import MUTATION_BUDGET, PromptMutator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OptimizationResult:
    proposed_changes: tuple[ProposedChange, ...]
    eval_results: tuple[EvalResult, ...]


def _build_rationale(
    cluster: FailureCluster,
    failure_contexts: list[str],
    baseline_prompt: str,
    candidate_prompt: str,
    report: EvalReport,
) -> str:
    excerpt = failure_contexts[0][:300].replace("\n", " ") if failure_contexts else "(no example available)"
    sig = report.significance
    return (
        f"Target failure: {cluster.description} ({cluster.size} cases in cluster '{cluster.label}')\n"
        f"\n"
        f"Representative failure:\n"
        f"> {excerpt}\n"
        f"\n"
        f"Prompt change:\n"
        f"  Before: {baseline_prompt[:200]}\n"
        f"  After:  {candidate_prompt[:200]}\n"
        f"\n"
        f"Eval result (holdout n={sig.sample_size}):\n"
        f"  Baseline score : {report.baseline_score:.3f}\n"
        f"  Candidate score: {report.candidate_score:.3f}\n"
        f"  Improvement    : +{sig.delta:.3f}\n"
        f"  p-value        : {sig.p_value:.4f}\n"
        f"  Judge agreement: {report.judge_agreement_rate:.1%}\n"
    )


class Optimizer:
    """GEPA optimization engine: cluster failures → mutate prompt → eval gate → ProposedChange.

    For each cluster:
      1. Extract up to 3 failure context examples.
      2. Call mutator.mutate() to generate `budget` candidate prompts.
      3. Evaluate each candidate via the eval harness (significance-gated).
      4. Keep the best survivor (highest delta that passes p < 0.05).
      5. Emit one ProposedChange per cluster that has a survivor.

    Usage:
        optimizer = Optimizer(mutator=FakeMutator(), harness=harness)
        result = optimizer.optimize(clusters, traces, baseline, holdout, run_id="run-1")
    """

    def __init__(
        self,
        mutator: PromptMutator,
        harness: EvalHarness,
        budget: int = MUTATION_BUDGET,
    ) -> None:
        self._mutator = mutator
        self._harness = harness
        self._budget = budget

    def optimize(
        self,
        clusters: list[FailureCluster],
        traces: list[Trace],
        baseline: AgentConfig,
        holdout: HoldoutSet,
        run_id: str,
    ) -> OptimizationResult:
        trace_by_id = {t.id: t for t in traces}
        proposed_changes: list[ProposedChange] = []
        eval_results: list[EvalResult] = []

        for cluster in clusters:
            failure_contexts = [
                extract_context(trace_by_id[tid])
                for tid in cluster.trace_ids[:3]
                if tid in trace_by_id
            ]

            candidates = self._mutator.mutate(baseline.prompt, failure_contexts, self._budget)
            logger.info(
                "Cluster '%s': evaluating %d candidates (budget=%d)",
                cluster.label,
                len(candidates),
                self._budget,
            )

            best_change: ProposedChange | None = None
            best_eval: EvalResult | None = None
            best_delta = 0.0

            for candidate_prompt in candidates:
                candidate = AgentConfig(prompt=candidate_prompt, skills=baseline.skills)
                try:
                    report = self._harness.evaluate(baseline, candidate, holdout)
                except JudgeCalibrationError as exc:
                    logger.warning("Judge calibration failed for cluster '%s': %s", cluster.label, exc)
                    break

                logger.debug(
                    "Cluster '%s' candidate delta=%.3f p=%.4f passed=%s",
                    cluster.label,
                    report.significance.delta,
                    report.significance.p_value,
                    report.significance.passed,
                )

                if report.passed and report.significance.delta > best_delta:
                    change_id = str(uuid.uuid4())
                    eval_result = EvalResult(
                        proposed_change_id=change_id,
                        baseline_score=report.baseline_score,
                        candidate_score=report.candidate_score,
                        delta=report.significance.delta,
                        p_value=report.significance.p_value,
                        sample_size=report.significance.sample_size,
                        passed=True,
                        judge_agreement_rate=report.judge_agreement_rate,
                    )
                    change = ProposedChange(
                        id=change_id,
                        optimization_run_id=run_id,
                        target="system_prompt",
                        before=baseline.prompt,
                        after=candidate_prompt,
                        rationale=_build_rationale(
                            cluster, failure_contexts, baseline.prompt, candidate_prompt, report
                        ),
                        eval_result_id=eval_result.id,
                    )
                    best_change = change
                    best_eval = eval_result
                    best_delta = report.significance.delta

            if best_change is not None and best_eval is not None:
                proposed_changes.append(best_change)
                eval_results.append(best_eval)
                logger.info(
                    "Cluster '%s': accepted candidate (delta=%.3f)", cluster.label, best_delta
                )
            else:
                logger.info("Cluster '%s': no candidate beat baseline", cluster.label)

        return OptimizationResult(
            proposed_changes=tuple(proposed_changes),
            eval_results=tuple(eval_results),
        )
