from __future__ import annotations

from dataclasses import dataclass

from core.clustering.context import extract_context
from core.eval.runner import AgentConfig, AgentRunner
from core.eval.scoring import EvalJudge, calibrate
from core.eval.split import EvalCase, HoldoutSet
from core.eval.stats import SignificanceResult, paired_t_test


@dataclass(frozen=True)
class CaseResult:
    case: EvalCase
    baseline_score: float
    candidate_score: float


@dataclass(frozen=True)
class EvalReport:
    case_results: tuple[CaseResult, ...]
    significance: SignificanceResult
    judge_agreement_rate: float

    @property
    def baseline_score(self) -> float:
        if not self.case_results:
            return 0.0
        return sum(r.baseline_score for r in self.case_results) / len(self.case_results)

    @property
    def candidate_score(self) -> float:
        if not self.case_results:
            return 0.0
        return sum(r.candidate_score for r in self.case_results) / len(self.case_results)

    @property
    def passed(self) -> bool:
        return self.significance.passed


class EvalHarness:
    """Runs a candidate AgentConfig against a HoldoutSet and returns an EvalReport.

    Usage:
        train, holdout = split(traces)
        harness = EvalHarness(runner, judge, seed_contexts, seed_labels)
        report = harness.evaluate(baseline_config, candidate_config, holdout)
    """

    def __init__(
        self,
        runner: AgentRunner,
        judge: EvalJudge,
        seed_contexts: list[str],
        seed_labels: list[str],
    ) -> None:
        self._runner = runner
        self._judge = judge
        self._seed_contexts = seed_contexts
        self._seed_labels = seed_labels

    def evaluate(
        self,
        baseline: AgentConfig,
        candidate: AgentConfig,
        holdout: HoldoutSet,
    ) -> EvalReport:
        """Calibrate judge, score both configs on holdout, run significance test."""
        agreement_rate = calibrate(self._judge, self._seed_contexts, self._seed_labels)

        case_results: list[CaseResult] = []
        for eval_case in holdout.cases:
            ctx = extract_context(eval_case.trace)
            baseline_response = self._runner.run(eval_case.trace, baseline)
            candidate_response = self._runner.run(eval_case.trace, candidate)
            baseline_score = self._judge.score(baseline_response or ctx)
            candidate_score = self._judge.score(candidate_response or ctx)
            case_results.append(CaseResult(eval_case, baseline_score, candidate_score))

        significance = paired_t_test(
            [r.baseline_score for r in case_results],
            [r.candidate_score for r in case_results],
        )

        return EvalReport(
            case_results=tuple(case_results),
            significance=significance,
            judge_agreement_rate=agreement_rate,
        )
