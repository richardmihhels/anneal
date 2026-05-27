from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from core.clustering.embedder import Embedder, TFIDFEmbedder
from core.clustering.judge import FakeJudge, LLMJudge
from core.clustering.labeler import ClusterLabeler, FakeLabeler
from core.eval.runner import AgentRunner, FakeAgentRunner
from core.eval.scoring import EvalJudge, FakeEvalJudge
from core.optimizer.mutator import MUTATION_BUDGET, FakeMutator, PromptMutator


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class CustomerConfig:
    """All static configuration Anneal needs to run one customer's weekly job."""

    agent_id: str
    repo: str          # "owner/name"
    config_path: str   # path inside repo, e.g. "agent/prompts.py"
    baseline_prompt: str
    seed_contexts: tuple[str, ...]   # human-labeled calibration examples
    seed_labels: tuple[str, ...]     # "pass" | "fail" for each context
    baseline_skills: tuple[str, ...] = ()
    base_branch: str = "main"


@dataclass(frozen=True)
class RunEvent:
    """One entry in the per-run timeline. Stored in Postgres; rendered by the dashboard."""

    run_id: str
    stage: Literal["init", "clustering", "optimization", "publishing", "done"]
    event: Literal["started", "completed", "failed", "info"]
    message: str
    id: str = field(default_factory=_uid)
    ts: datetime = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineComponents:
    """Injectable ML/LLM components. Swap fakes in tests, real impls in production."""

    embedder: Embedder
    clustering_judge: LLMJudge
    labeler: ClusterLabeler
    mutator: PromptMutator
    eval_runner: AgentRunner
    eval_judge: EvalJudge
    mutation_budget: int = MUTATION_BUDGET


def fake_components() -> PipelineComponents:
    """All-fake components for tests and offline demos. No API keys required."""
    return PipelineComponents(
        embedder=TFIDFEmbedder(),
        clustering_judge=FakeJudge(),
        labeler=FakeLabeler(),
        mutator=FakeMutator(),
        eval_runner=FakeAgentRunner(pass_rate=0.5),
        eval_judge=FakeEvalJudge(default_score=1.0),
    )
