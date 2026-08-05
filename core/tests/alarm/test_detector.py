"""Tests: spike detection, normal-variance silence, debounce, Alarm record, email format."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from core.alarm.detector import AlarmDetector, _proportions_ztest
from core.alarm.notifier import FakeEmailNotifier, _format_email_body, _format_subject
from core.alarm.store import FakeAlarmStore
from core.testing.generator import generate_dataset, generate_dataset_with_spike
from shared.models import Alarm

# ── unit: proportions z-test ──────────────────────────────────────────────────


def test_proportions_ztest_clear_spike() -> None:
    """High spike should produce p << 0.05."""
    p = _proportions_ztest(x1=30, n1=50, x2=3, n2=50)
    assert p < 0.01


def test_proportions_ztest_no_spike() -> None:
    """Equal rates should return p=1.0 (no spike)."""
    p = _proportions_ztest(x1=10, n1=100, x2=10, n2=100)
    assert p == 1.0


def test_proportions_ztest_insufficient_data() -> None:
    """Too few traces per window should return p=1.0."""
    p = _proportions_ztest(x1=3, n1=4, x2=1, n2=4)
    assert p == 1.0


# ── integration: spike detected ───────────────────────────────────────────────


def test_spike_detected() -> None:
    """Injected spike should fire exactly one Alarm for the spiked category."""
    spike_category = "hallucinated_policy"
    traces = generate_dataset_with_spike(
        n_baseline=100,
        n_spike=60,
        spike_category=spike_category,
        spike_rate=0.65,
        seed=7,
        window_hours=24,
    )

    detector = AlarmDetector(window_hours=24)
    alarms = detector.detect(traces=traces, agent_id="test-agent")

    assert len(alarms) >= 1
    categories = [a.category for a in alarms]
    assert spike_category in categories

    alarm = next(a for a in alarms if a.category == spike_category)
    assert alarm.current_rate > alarm.baseline_rate
    assert alarm.affected_trace_count >= 3
    assert alarm.window_hours == 24
    assert alarm.agent_id == "test-agent"
    assert "Hypothesis" in alarm.cause_hypothesis


def test_normal_variance_silent() -> None:
    """Normal distribution should not trigger any alarms."""
    traces = generate_dataset(n=200, seed=42)
    # Spread traces evenly across a 48-hour window
    now = datetime.now(UTC).replace(microsecond=0)
    for i, t in enumerate(traces):
        # First half: baseline window, second half: current window
        offset = timedelta(hours=47 - (i * 47 / len(traces)))
        object.__setattr__(t, "created_at", now - offset)

    detector = AlarmDetector(window_hours=24)
    alarms = detector.detect(traces=traces, agent_id="test-agent")

    assert alarms == [], f"Expected no alarms, got: {[a.category for a in alarms]}"


# ── debounce ──────────────────────────────────────────────────────────────────


def test_debounce_suppresses_repeat() -> None:
    """Alarm for a category already fired in the last 24h should be suppressed."""
    spike_category = "wrong_tool"
    traces = generate_dataset_with_spike(
        n_baseline=100,
        n_spike=60,
        spike_category=spike_category,
        spike_rate=0.65,
        seed=13,
        window_hours=24,
    )
    recent_alarm = Alarm(
        agent_id="test-agent",
        category=spike_category,
        baseline_rate=0.05,
        current_rate=0.40,
        window_hours=24,
        affected_trace_count=24,
        first_detected=datetime.now(UTC) - timedelta(hours=2),
        cause_hypothesis="prior alarm",
    )

    detector = AlarmDetector(window_hours=24)
    alarms = detector.detect(
        traces=traces,
        agent_id="test-agent",
        recent_alarms=[recent_alarm],
    )

    categories = [a.category for a in alarms]
    assert spike_category not in categories, "Debounce should have suppressed this alarm"


def test_debounce_fires_after_window() -> None:
    """Alarm should fire again after the debounce window expires."""
    spike_category = "wrong_tool"
    traces = generate_dataset_with_spike(
        n_baseline=100,
        n_spike=60,
        spike_category=spike_category,
        spike_rate=0.65,
        seed=13,
        window_hours=24,
    )
    # Alarm from 25 hours ago — debounce expired
    stale_alarm = Alarm(
        agent_id="test-agent",
        category=spike_category,
        baseline_rate=0.05,
        current_rate=0.40,
        window_hours=24,
        affected_trace_count=24,
        first_detected=datetime.now(UTC) - timedelta(hours=25),
        cause_hypothesis="old alarm",
    )

    detector = AlarmDetector(window_hours=24)
    alarms = detector.detect(
        traces=traces,
        agent_id="test-agent",
        recent_alarms=[stale_alarm],
    )

    categories = [a.category for a in alarms]
    assert spike_category in categories, "Alarm should re-fire after debounce window"


# ── Alarm record fields ───────────────────────────────────────────────────────


def test_alarm_record_fields() -> None:
    """Alarm model should have all required fields with correct types."""
    alarm = Alarm(
        agent_id="my-agent",
        category="policy_violation",
        baseline_rate=0.04,
        current_rate=0.22,
        window_hours=24,
        affected_trace_count=11,
        cause_hypothesis="Hypothesis (AI-generated — treat as a guess): some guess.",
    )
    assert alarm.id  # auto-generated UUID
    assert alarm.organization_id == "org_demo"
    assert alarm.notified is False
    assert alarm.first_detected is not None
    assert 0 <= alarm.baseline_rate <= 1
    assert 0 <= alarm.current_rate <= 1


# ── Email format ──────────────────────────────────────────────────────────────


def test_email_body_contains_required_fields() -> None:
    """Email body must include category, rates, affected count, and hypothesis."""
    alarm = Alarm(
        agent_id="cascade-support-v1",
        category="hallucinated_policy",
        baseline_rate=0.05,
        current_rate=0.32,
        window_hours=24,
        affected_trace_count=19,
        cause_hypothesis="Hypothesis (AI-generated — treat as a guess): possible data drift.",
    )
    body = _format_email_body(alarm)
    subject = _format_subject(alarm)

    assert "hallucinated_policy" in body
    assert "5.0%" in body  # baseline_rate formatted as percent
    assert "32.0%" in body  # current_rate
    assert "19" in body  # affected count
    assert "treat as a guess" in body
    assert "Anneal" in subject
    assert "hallucinated_policy" in subject


def test_fake_email_notifier_captures_send() -> None:
    """FakeEmailNotifier should capture sent alarms for test assertions."""
    alarm = Alarm(
        agent_id="agent-x",
        category="scope_creep",
        baseline_rate=0.02,
        current_rate=0.18,
        window_hours=24,
        affected_trace_count=9,
        cause_hypothesis="Hypothesis (AI-generated — treat as a guess): some guess.",
    )
    notifier = FakeEmailNotifier()
    notifier.send(alarm)

    assert len(notifier.sent) == 1
    assert notifier.sent[0]["alarm_id"] == alarm.id
    assert "scope_creep" in notifier.sent[0]["subject"]


# ── FakeAlarmStore ────────────────────────────────────────────────────────────


def test_fake_alarm_store_debounce_lookup() -> None:
    """FakeAlarmStore.get_recent_alarm should return within-window alarms only."""
    store = FakeAlarmStore()

    old_alarm = Alarm(
        agent_id="a",
        category="wrong_tool",
        baseline_rate=0.05,
        current_rate=0.3,
        window_hours=24,
        affected_trace_count=5,
        first_detected=datetime.now(UTC) - timedelta(hours=30),
        cause_hypothesis="old",
    )
    recent_alarm = Alarm(
        agent_id="a",
        category="wrong_tool",
        baseline_rate=0.05,
        current_rate=0.3,
        window_hours=24,
        affected_trace_count=5,
        first_detected=datetime.now(UTC) - timedelta(hours=2),
        cause_hypothesis="recent",
    )

    async def _run() -> None:
        await store.save_alarm(old_alarm)
        await store.save_alarm(recent_alarm)

        result = await store.get_recent_alarm("org_demo", "a", "wrong_tool", within_hours=24)
        assert result is not None
        assert result.id == recent_alarm.id

        # Different category → None
        result2 = await store.get_recent_alarm("org_demo", "a", "scope_creep", within_hours=24)
        assert result2 is None

    asyncio.run(_run())
