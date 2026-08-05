from __future__ import annotations

import asyncio

from core.alarm.notifier import FakeEmailNotifier
from core.alarm.store import FakeAlarmStore
from core.testing.generator import generate_dataset_with_spike
from shared.models import Trace
from worker.alarms import run_alarm_cycle
from worker.models import CustomerConfig


def test_alarm_cycle_persists_and_notifies() -> None:
    customer = CustomerConfig(
        organization_id="org_acme",
        agent_id="cascade-support-v1",
        repo="acme/agent",
        config_path="agent/prompts.py",
        baseline_prompt="baseline",
        seed_contexts=("pass", "pass", "fail", "fail"),
        seed_labels=("pass", "pass", "fail", "fail"),
    )
    traces = generate_dataset_with_spike(
        n_baseline=100,
        n_spike=60,
        spike_category="hallucinated_policy",
        spike_rate=0.75,
        seed=71,
    )

    async def get_traces(organization_id: str, agent_id: str) -> list[Trace]:
        assert organization_id == customer.organization_id
        assert agent_id == customer.agent_id
        return [
            trace.model_copy(
                update={
                    "organization_id": organization_id,
                    "agent_id": agent_id,
                }
            )
            for trace in traces
        ]

    store = FakeAlarmStore()
    notifier = FakeEmailNotifier()
    fired = asyncio.run(run_alarm_cycle([customer], get_traces, store, notifier))

    assert fired
    assert store.all_alarms == fired
    assert len(notifier.sent) == len(fired)
    assert all(alarm.organization_id == "org_acme" for alarm in fired)
