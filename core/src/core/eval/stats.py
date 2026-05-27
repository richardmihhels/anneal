from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

_SIGNIFICANCE_LEVEL = 0.05


@dataclass(frozen=True)
class SignificanceResult:
    delta: float
    p_value: float
    passed: bool
    sample_size: int


def paired_t_test(baseline_scores: list[float], candidate_scores: list[float]) -> SignificanceResult:
    """One-tailed paired t-test: H1 = candidate > baseline.

    Returns passed=True only when delta > 0 AND p < 0.05.
    """
    if len(baseline_scores) != len(candidate_scores):
        raise ValueError("baseline and candidate score lists must be the same length")
    if len(baseline_scores) < 2:
        return SignificanceResult(delta=0.0, p_value=1.0, passed=False, sample_size=len(baseline_scores))

    b: NDArray[np.float64] = np.array(baseline_scores, dtype=np.float64)
    c: NDArray[np.float64] = np.array(candidate_scores, dtype=np.float64)
    delta = float(np.mean(c) - np.mean(b))

    if delta <= 0:
        return SignificanceResult(delta=delta, p_value=1.0, passed=False, sample_size=len(baseline_scores))

    from scipy import stats  # type: ignore[import-untyped]

    _, two_tailed_p = stats.ttest_rel(c, b)
    p_value = float(two_tailed_p) / 2  # one-tailed

    return SignificanceResult(
        delta=delta,
        p_value=p_value,
        passed=p_value < _SIGNIFICANCE_LEVEL,
        sample_size=len(baseline_scores),
    )
