from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from shared.models import Trace

_TOKEN = object()
_HOLDOUT_FRACTION = 0.2


@dataclass(frozen=True)
class EvalCase:
    trace: Trace
    human_label: str  # "pass" | "fail"


@dataclass(frozen=True)
class HoldoutSet:
    cases: tuple[EvalCase, ...]
    _token: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _TOKEN:
            raise RuntimeError(
                "HoldoutSet must be created via eval.split() — never construct directly. "
                "Direct construction would allow optimization code to inspect the holdout."
            )


@dataclass(frozen=True)
class TrainSet:
    cases: tuple[EvalCase, ...]


def _holdout_fraction(seed: int, trace_id: str) -> float:
    """Deterministic hash of (seed, trace_id) → float in [0, 1)."""
    digest = hashlib.sha256(f"{seed}:{trace_id}".encode()).hexdigest()
    return int(digest[-8:], 16) / 0xFFFFFFFF


def split(traces: list[Trace], seed: int = 42) -> tuple[TrainSet, HoldoutSet]:
    """Split traces into train/holdout using deterministic hash-based assignment.

    Holdout fraction is fixed at 20%. Structural token prevents HoldoutSet
    from being constructed outside this function.
    """
    train_cases: list[EvalCase] = []
    holdout_cases: list[EvalCase] = []

    for trace in traces:
        label = "fail" if trace.outcome == "failure" else "pass"
        case = EvalCase(trace=trace, human_label=label)
        if _holdout_fraction(seed, trace.id) < _HOLDOUT_FRACTION:
            holdout_cases.append(case)
        else:
            train_cases.append(case)

    return (
        TrainSet(cases=tuple(train_cases)),
        HoldoutSet(cases=tuple(holdout_cases), _token=_TOKEN),
    )
