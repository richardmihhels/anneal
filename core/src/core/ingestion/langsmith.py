from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from shared.models import Span, Trace


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def _flatten(run: dict[str, Any], trace_id: str) -> list[Span]:
    start = _dt(run["start_time"])
    end_raw = run.get("end_time")
    end = _dt(end_raw) if end_raw else start
    duration_ms = max((end - start).total_seconds() * 1000, 0.0)

    extra_meta: dict[str, Any] = (run.get("extra") or {}).get("metadata") or {}

    span = Span(
        id=run["id"],
        trace_id=trace_id,
        name=run.get("name", "unknown"),
        start_time=start,
        end_time=end,
        duration_ms=duration_ms,
        input=run.get("inputs") or {},
        output=run.get("outputs") or {},
        error=run.get("error"),
        metadata=extra_meta,
    )

    spans: list[Span] = [span]
    for child in run.get("child_runs") or []:
        spans.extend(_flatten(child, trace_id))
    return spans


def _agent_id(run: dict[str, Any]) -> str:
    for tag in run.get("tags") or []:
        if isinstance(tag, str) and tag.startswith("agent_id:"):
            return tag[9:]
    extra_meta: dict[str, Any] = (run.get("extra") or {}).get("metadata") or {}
    return str(extra_meta.get("agent_id", run.get("name", "unknown")))


def normalize_langsmith(payload: dict[str, Any]) -> Trace:
    """Convert a LangSmith/Langfuse run export into a Trace.

    The top-level run maps to the Trace; nested child_runs become Spans.
    For Langfuse observations, wrap in {"id": ..., "child_runs": [...]} first.
    """
    trace_id: str = str(payload.get("session_id") or payload["id"])
    created_at = _dt(payload["start_time"])
    extra_meta: dict[str, Any] = (payload.get("extra") or {}).get("metadata") or {}
    declared_outcome = extra_meta.get("outcome")
    outcome: Literal["success", "failure", "unknown"]
    if declared_outcome == "success":
        outcome = "success"
    elif declared_outcome == "failure":
        outcome = "failure"
    elif declared_outcome == "unknown":
        outcome = "unknown"
    elif payload.get("error") or extra_meta.get("failure_category"):
        outcome = "failure"
    else:
        outcome = "unknown"

    return Trace(
        id=trace_id,
        agent_id=_agent_id(payload),
        session_id=str(payload.get("session_id") or trace_id),
        created_at=created_at,
        spans=_flatten(payload, trace_id),
        outcome=outcome,
        metadata=extra_meta,
    )
