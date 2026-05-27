from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from shared.models import Span, Trace


def _ns_to_dt(ns: str | int) -> datetime:
    return datetime.fromtimestamp(int(ns) / 1_000_000_000, tz=UTC)


def _attr_val(v: dict[str, Any]) -> Any:
    for key in ("stringValue", "intValue", "doubleValue", "boolValue", "arrayValue"):
        if key in v:
            raw = v[key]
            if key == "stringValue":
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    return raw
            return raw
    return None


def _attrs(attrs: list[dict[str, Any]]) -> dict[str, Any]:
    return {a["key"]: _attr_val(a["value"]) for a in attrs if "value" in a}


def normalize_otel(payload: dict[str, Any]) -> list[Trace]:
    """Convert an OTLP JSON export into a list of Trace objects (one per traceId)."""
    traces: dict[str, Trace] = {}

    for rs in payload.get("resourceSpans", []):
        res_attrs = _attrs(rs.get("resource", {}).get("attributes", []))
        agent_id: str = str(res_attrs.get("agent.id", "unknown"))
        session_id: str = str(res_attrs.get("session.id", "unknown"))

        for ss in rs.get("scopeSpans", []):
            for sd in ss.get("spans", []):
                trace_id: str = sd["traceId"]
                span_id: str = sd["spanId"]
                span_attrs = _attrs(sd.get("attributes", []))

                start = _ns_to_dt(sd["startTimeUnixNano"])
                end = _ns_to_dt(sd["endTimeUnixNano"])
                duration_ms = (end - start).total_seconds() * 1000

                status = sd.get("status", {})
                error: str | None = (
                    str(status["message"]) if status.get("code", 0) != 0 and "message" in status else None
                )

                span = Span(
                    id=span_id,
                    trace_id=trace_id,
                    name=sd.get("name", "unknown"),
                    start_time=start,
                    end_time=end,
                    duration_ms=max(duration_ms, 0.0),
                    input=span_attrs.get("input") or {},
                    output=span_attrs.get("output") or {},
                    error=error,
                    metadata={k: v for k, v in span_attrs.items() if k not in ("input", "output")},
                )

                if trace_id not in traces:
                    traces[trace_id] = Trace(
                        id=trace_id,
                        agent_id=agent_id,
                        session_id=session_id,
                        created_at=start,
                        spans=[],
                    )
                traces[trace_id].spans.append(span)

    return list(traces.values())
