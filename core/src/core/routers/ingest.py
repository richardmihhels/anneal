from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from shared.models import Trace

from core.auth import require_organization
from core.db.repositories import FakeSpanRepo, FakeTraceRepo, SpanRepo, TraceRepo
from core.ingestion import normalize_langsmith, normalize_otel, scrub

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ── dependency providers (overridden in tests / prod startup) ─────────────────

_trace_repo: TraceRepo = FakeTraceRepo()
_span_repo: SpanRepo = FakeSpanRepo()


def get_trace_repo() -> TraceRepo:
    return _trace_repo


def get_span_repo() -> SpanRepo:
    return _span_repo


def set_repos(trace_repo: TraceRepo, span_repo: SpanRepo) -> None:
    global _trace_repo, _span_repo
    _trace_repo = trace_repo
    _span_repo = span_repo


# ── helpers ───────────────────────────────────────────────────────────────────


async def _persist(
    trace: Trace,
    trace_repo: TraceRepo,
    span_repo: SpanRepo,
) -> None:
    await trace_repo.save(trace)
    await span_repo.save_many(trace.spans, trace.organization_id, trace.agent_id, trace.session_id)


# ── endpoints ─────────────────────────────────────────────────────────────────


@router.post("/otel")
async def ingest_otel(
    payload: dict[str, Any],
    trace_repo: Annotated[TraceRepo, Depends(get_trace_repo)],
    span_repo: Annotated[SpanRepo, Depends(get_span_repo)],
    organization_id: Annotated[str, Depends(require_organization)],
) -> dict[str, Any]:
    """Accept an OTLP JSON export (resourceSpans format)."""
    clean = scrub(payload)
    traces = normalize_otel(clean)
    if not traces:
        raise HTTPException(status_code=422, detail="No spans found in payload")
    for trace in traces:
        trace = trace.model_copy(update={"organization_id": organization_id})
        await _persist(trace, trace_repo, span_repo)
    return {"ingested": len(traces), "trace_ids": [t.id for t in traces]}


@router.post("/langsmith")
async def ingest_langsmith(
    payload: dict[str, Any],
    trace_repo: Annotated[TraceRepo, Depends(get_trace_repo)],
    span_repo: Annotated[SpanRepo, Depends(get_span_repo)],
    organization_id: Annotated[str, Depends(require_organization)],
) -> dict[str, Any]:
    """Accept a LangSmith (or Langfuse) run export."""
    clean = scrub(payload)
    trace = normalize_langsmith(clean)
    trace = trace.model_copy(update={"organization_id": organization_id})
    await _persist(trace, trace_repo, span_repo)
    return {"ingested": 1, "trace_ids": [trace.id]}
