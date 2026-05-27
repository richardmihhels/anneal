from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class Span(BaseModel):
    id: str = Field(default_factory=_uuid)
    trace_id: str
    name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    id: str = Field(default_factory=_uuid)
    organization_id: str = "org_demo"
    agent_id: str
    session_id: str
    created_at: datetime = Field(default_factory=_now)
    spans: list[Span] = Field(default_factory=list)
    outcome: Literal["success", "failure", "unknown"] = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FailureCluster(BaseModel):
    id: str = Field(default_factory=_uuid)
    label: str
    description: str
    trace_ids: list[str] = Field(default_factory=list)
    size: int = 0
    created_at: datetime = Field(default_factory=_now)
    representative_trace_id: str | None = None


class OptimizationRun(BaseModel):
    id: str = Field(default_factory=_uuid)
    organization_id: str = "org_demo"
    agent_id: str
    created_at: datetime = Field(default_factory=_now)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    cluster_ids: list[str] = Field(default_factory=list)
    proposed_change_ids: list[str] = Field(default_factory=list)


class ProposedChange(BaseModel):
    id: str = Field(default_factory=_uuid)
    optimization_run_id: str
    target: str
    before: str
    after: str
    rationale: str
    eval_result_id: str | None = None


class EvalResult(BaseModel):
    id: str = Field(default_factory=_uuid)
    proposed_change_id: str
    run_at: datetime = Field(default_factory=_now)
    baseline_score: float
    candidate_score: float
    delta: float
    p_value: float
    sample_size: int
    passed: bool
    judge_agreement_rate: float
