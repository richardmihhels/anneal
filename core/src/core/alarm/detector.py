"""Regression alarm detector: per-category failure rate spike detection.

Watches a rolling trace stream. Fires an Alarm when a failure category's rate
rises significantly above its recent baseline (one-sided proportions z-test,
p < 0.05). Debounces repeat alarms for the same ongoing spike.

Opinionated defaults:
  - window_hours=24: compare last 24 h vs previous 24 h
  - alpha=0.05: significance threshold
  - debounce_hours=24: suppress repeat alarms for the same category
  - min_affected=3: require at least 3 failing traces before alarming
  - min_window_traces=5: require at least 5 total traces per window
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable

from shared.models import Alarm, Trace

logger = logging.getLogger(__name__)

_ALPHA = 0.05
_DEBOUNCE_HOURS = 24
_MIN_AFFECTED = 3
_MIN_WINDOW_TRACES = 5


@runtime_checkable
class HypothesisGenerator(Protocol):
    def generate(
        self,
        category: str,
        baseline_rate: float,
        current_rate: float,
        sample_descriptions: list[str],
    ) -> str: ...


class TemplateHypothesisGenerator:
    """Rule-based hypothesis for tests and fallback."""

    def generate(
        self,
        category: str,
        baseline_rate: float,
        current_rate: float,
        sample_descriptions: list[str],
    ) -> str:
        pct_change = (current_rate - baseline_rate) / max(baseline_rate, 1e-9) * 100
        sample_note = ""
        if sample_descriptions:
            sample_note = f' A recent example: "{sample_descriptions[0][:120]}".'
        return (
            f"Hypothesis (AI-generated — treat as a guess): The '{category}' failure rate "
            f"rose {pct_change:.0f}% from {baseline_rate:.1%} to {current_rate:.1%}. "
            f"This may indicate a recent change in upstream data, user behaviour, or an "
            f"environment shift.{sample_note}"
        )


def _proportions_ztest(x1: int, n1: int, x2: int, n2: int) -> float:
    """One-sided (right-tail) proportions z-test. Returns p-value for H1: p1 > p2."""
    if n1 < _MIN_WINDOW_TRACES or n2 < _MIN_WINDOW_TRACES:
        return 1.0
    p1 = x1 / n1
    p2 = x2 / n2
    if p1 <= p2:
        return 1.0
    p_hat = (x1 + x2) / (n1 + n2)
    variance = p_hat * (1.0 - p_hat) * (1.0 / n1 + 1.0 / n2)
    if variance <= 0:
        return 1.0
    z = (p1 - p2) / math.sqrt(variance)
    # Standard normal CDF approximation (avoids scipy import in this module)
    return _norm_sf(z)


def _norm_sf(z: float) -> float:
    """Survival function (1 - CDF) of the standard normal distribution."""
    # erfc(z/sqrt(2)) / 2 — accurate to ~7 decimal places
    import math

    return math.erfc(z / math.sqrt(2.0)) / 2.0


def _failure_category(trace: Trace) -> str | None:
    """Extract failure category label from trace metadata."""
    cat = trace.metadata.get("failure_category")
    if cat is None or cat == "":
        return None
    return str(cat)


def _sample_description(trace: Trace) -> str:
    """Short text description of a trace for hypothesis context."""
    for span in trace.spans:
        if span.name == "agent_turn":
            msgs = span.output.get("content") or span.input.get("messages", [])
            if isinstance(msgs, str) and msgs:
                return msgs[:160]
            if isinstance(msgs, list) and msgs:
                last = msgs[-1]
                if isinstance(last, dict):
                    return str(last.get("content", ""))[:160]
    return f"trace:{trace.id[:8]}"


class AlarmDetector:
    """Detect per-category failure rate spikes in a trace stream."""

    def __init__(
        self,
        window_hours: int = 24,
        hypothesis_gen: HypothesisGenerator | None = None,
    ) -> None:
        self._window_hours = window_hours
        self._hypothesis_gen: HypothesisGenerator = hypothesis_gen or TemplateHypothesisGenerator()

    def detect(
        self,
        traces: list[Trace],
        agent_id: str,
        organization_id: str = "org_demo",
        recent_alarms: list[Alarm] | None = None,
        now: datetime | None = None,
    ) -> list[Alarm]:
        """Return Alarm objects for categories with a statistically significant spike.

        Does NOT persist alarms — caller handles that. Debounce is evaluated
        against `recent_alarms` (alarms already in the store).
        """
        if now is None:
            now = datetime.now(UTC)

        current_start = now - timedelta(hours=self._window_hours)
        baseline_start = now - timedelta(hours=2 * self._window_hours)

        current_traces = [t for t in traces if current_start <= t.created_at <= now]
        baseline_traces = [t for t in traces if baseline_start <= t.created_at < current_start]

        n_current = len(current_traces)
        n_baseline = len(baseline_traces)

        if n_current < _MIN_WINDOW_TRACES or n_baseline < _MIN_WINDOW_TRACES:
            logger.debug(
                "AlarmDetector: not enough traces (current=%d baseline=%d min=%d)",
                n_current,
                n_baseline,
                _MIN_WINDOW_TRACES,
            )
            return []

        # Count failures per category in each window
        current_by_cat: dict[str, list[Trace]] = {}
        baseline_by_cat: dict[str, list[Trace]] = {}

        for t in current_traces:
            if t.outcome == "failure":
                cat = _failure_category(t) or "unknown"
                current_by_cat.setdefault(cat, []).append(t)

        for t in baseline_traces:
            if t.outcome == "failure":
                cat = _failure_category(t) or "unknown"
                baseline_by_cat.setdefault(cat, []).append(t)

        all_categories = set(current_by_cat) | set(baseline_by_cat)

        # Build debounce index: categories with a recent alarm
        debounced: set[str] = set()
        if recent_alarms:
            cutoff = now - timedelta(hours=_DEBOUNCE_HOURS)
            for alarm in recent_alarms:
                if alarm.agent_id == agent_id and alarm.first_detected >= cutoff:
                    debounced.add(alarm.category)

        alarms: list[Alarm] = []
        for cat in sorted(all_categories):
            x1 = len(current_by_cat.get(cat, []))
            x2 = len(baseline_by_cat.get(cat, []))

            if x1 < _MIN_AFFECTED:
                continue

            p_value = _proportions_ztest(x1, n_current, x2, n_baseline)
            if p_value >= _ALPHA:
                continue

            if cat in debounced:
                logger.debug("AlarmDetector: suppressing repeat alarm for category '%s'", cat)
                continue

            current_rate = x1 / n_current
            baseline_rate = x2 / n_baseline

            sample_descs = [_sample_description(t) for t in current_by_cat.get(cat, [])[:3]]
            hypothesis = self._hypothesis_gen.generate(cat, baseline_rate, current_rate, sample_descs)

            alarms.append(
                Alarm(
                    organization_id=organization_id,
                    agent_id=agent_id,
                    category=cat,
                    baseline_rate=baseline_rate,
                    current_rate=current_rate,
                    window_hours=self._window_hours,
                    affected_trace_count=x1,
                    cause_hypothesis=hypothesis,
                )
            )
            logger.info(
                "AlarmDetector: spike detected for '%s' — %.1f%% → %.1f%% (p=%.4f)",
                cat,
                baseline_rate * 100,
                current_rate * 100,
                p_value,
            )

        return alarms


async def run_alarm_check(
    traces: list[Trace],
    agent_id: str,
    organization_id: str,
    alarm_store: object,
    notifier: object,
    detector: AlarmDetector | None = None,
    now: datetime | None = None,
) -> list[Alarm]:
    """Convenience entry point: detect → persist → notify.

    Designed to be called from an ingest hook or a short-interval cron job
    (e.g., hourly), independent of the weekly optimization worker.
    """
    from core.alarm.notifier import AlarmNotifier
    from core.alarm.store import AlarmStore

    assert isinstance(alarm_store, AlarmStore)
    assert isinstance(notifier, AlarmNotifier)

    if detector is None:
        detector = AlarmDetector()

    # Load recent alarms for debounce
    recent_alarms: list[Alarm] = []
    for cat in {t.metadata.get("failure_category") for t in traces if t.metadata.get("failure_category")}:
        recent = await alarm_store.get_recent_alarm(
            organization_id,
            agent_id,
            str(cat),
            _DEBOUNCE_HOURS,
        )
        if recent is not None:
            recent_alarms.append(recent)

    fired = detector.detect(
        traces=traces,
        agent_id=agent_id,
        organization_id=organization_id,
        recent_alarms=recent_alarms,
        now=now,
    )

    for alarm in fired:
        await alarm_store.save_alarm(alarm)
        notifier.send(alarm)

    return fired
