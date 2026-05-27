from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from shared.models import Trace

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


def _org_id(trace: Trace, header_org_id: str | None) -> str:
    if header_org_id:
        return header_org_id
    metadata_org_id = trace.metadata.get("organization_id") or trace.metadata.get("org_id")
    return str(metadata_org_id or "org_demo")


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
    x_anneal_org: Annotated[str | None, Header(alias="X-Anneal-Org")] = None,
) -> dict[str, Any]:
    """Accept an OTLP JSON export (resourceSpans format)."""
    clean = scrub(payload)
    traces = normalize_otel(clean)
    if not traces:
        raise HTTPException(status_code=422, detail="No spans found in payload")
    for trace in traces:
        trace = trace.model_copy(update={"organization_id": _org_id(trace, x_anneal_org)})
        await _persist(trace, trace_repo, span_repo)
    return {"ingested": len(traces), "trace_ids": [t.id for t in traces]}


@router.post("/langsmith")
async def ingest_langsmith(
    payload: dict[str, Any],
    trace_repo: Annotated[TraceRepo, Depends(get_trace_repo)],
    span_repo: Annotated[SpanRepo, Depends(get_span_repo)],
    x_anneal_org: Annotated[str | None, Header(alias="X-Anneal-Org")] = None,
) -> dict[str, Any]:
    """Accept a LangSmith (or Langfuse) run export."""
    clean = scrub(payload)
    trace = normalize_langsmith(clean)
    trace = trace.model_copy(update={"organization_id": _org_id(trace, x_anneal_org)})
    await _persist(trace, trace_repo, span_repo)
    return {"ingested": 1, "trace_ids": [trace.id]}
