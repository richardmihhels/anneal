"""Short-interval regression alarm orchestration."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from core.alarm.detector import run_alarm_check
from core.alarm.notifier import AlarmNotifier
from core.alarm.store import AlarmStore
from shared.models import Alarm, Trace

from worker.models import CustomerConfig


async def run_alarm_cycle(
    customers: list[CustomerConfig],
    get_traces: Callable[[str, str], Coroutine[Any, Any, list[Trace]]],
    store: AlarmStore,
    notifier: AlarmNotifier,
) -> list[Alarm]:
    """Detect, persist, and notify for every configured customer."""
    fired: list[Alarm] = []
    for customer in customers:
        traces = await get_traces(customer.organization_id, customer.agent_id)
        fired.extend(
            await run_alarm_check(
                traces=traces,
                agent_id=customer.agent_id,
                organization_id=customer.organization_id,
                alarm_store=store,
                notifier=notifier,
            )
        )
    return fired
