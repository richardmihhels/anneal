from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import numpy as np
from numpy.typing import NDArray
from shared.models import FailureCluster, Trace

from .context import extract_context
from .embedder import Embedder, TFIDFEmbedder
from .judge import FakeJudge, LLMJudge
from .labeler import ClusterLabeler, FakeLabeler

logger = logging.getLogger(__name__)

# Minimum number of traces sharing a root cause before Anneal surfaces a cluster.
#
# Rationale for 5: the downstream optimization step (GEPA, Prompt 5) requires a
# before/after eval comparison; anything below ~5 examples has too wide a
# confidence interval to gate a prompt change. Five is also the practical floor
# for "this failure is reproducible and worth fixing" rather than a one-off edge
# case. For high-volume production agents (>10k traces/week), raise to 10-15
# via the pipeline constructor — but never surface this as a user-facing config
# knob, because "how many failures count?" is an engineering constant, not a
# business preference.
_MIN_CLUSTER_SIZE = 5


class ClusterPipeline:
    """End-to-end pipeline: identify failures → embed → cluster → label.

    Inject fakes for judge/labeler/embedder in tests; use real implementations
    for production. All three are pure protocols — no shared state.
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        judge: LLMJudge | None = None,
        labeler: ClusterLabeler | None = None,
        min_cluster_size: int = _MIN_CLUSTER_SIZE,
    ) -> None:
        self._embedder: Embedder = embedder or TFIDFEmbedder()
        self._judge: LLMJudge = judge or FakeJudge()
        self._labeler: ClusterLabeler = labeler or FakeLabeler()
        self._min_cluster_size = min_cluster_size

    # ── public API ────────────────────────────────────────────────────────────

    def run(self, traces: list[Trace]) -> list[FailureCluster]:
        """Cluster failure traces and return FailureCluster objects."""
        failures = self._identify_failures(traces)
        logger.info("Identified %d failure traces from %d total", len(failures), len(traces))

        if len(failures) < self._min_cluster_size:
            logger.info("Too few failures to cluster (%d < %d)", len(failures), self._min_cluster_size)
            return []

        contexts = [extract_context(t) for t in failures]
        X = self._embedder.embed(contexts)

        labels = self._hdbscan(X)

        n_noise = int((labels == -1).sum())
        n_clusters = int(labels.max()) + 1 if labels.max() >= 0 else 0
        logger.info("HDBSCAN: %d clusters, %d noise points discarded", n_clusters, n_noise)

        return self._build_clusters(failures, contexts, X, labels)

    def calibrate_judge(self, labeled_traces: list[Trace]) -> float:
        """Measure judge agreement against human outcome labels.

        Must be run against the seed set before trusting production clustering.
        Logs the agreement rate so it can be tracked over model versions.
        """
        if not labeled_traces:
            return 0.0
        agreed = 0
        for trace in labeled_traces:
            human = trace.outcome == "failure"
            judge = self._judge.is_failure(extract_context(trace))
            if human == judge:
                agreed += 1
        rate = agreed / len(labeled_traces)
        logger.info(
            "judge_calibration agreement_rate=%.3f n=%d",
            rate,
            len(labeled_traces),
        )
        return rate

    # ── internals ─────────────────────────────────────────────────────────────

    def _identify_failures(self, traces: list[Trace]) -> list[Trace]:
        result: list[Trace] = []
        for trace in traces:
            if trace.outcome == "failure":
                result.append(trace)
            elif trace.outcome == "unknown":
                if self._judge.is_failure(extract_context(trace)):
                    result.append(trace)
        return result

    def _hdbscan(self, X: NDArray[np.float32]) -> NDArray[Any]:
        from sklearn.cluster import HDBSCAN  # type: ignore[import-untyped]

        # HDBSCAN requires min_cluster_size >= 2
        hdb = HDBSCAN(min_cluster_size=max(self._min_cluster_size, 2), metric="euclidean")
        labels: NDArray[Any] = hdb.fit_predict(X)
        return labels

    def _build_clusters(
        self,
        failures: list[Trace],
        contexts: list[str],
        X: NDArray[np.float32],
        labels: NDArray[Any],
    ) -> list[FailureCluster]:
        by_label: dict[int, list[int]] = defaultdict(list)
        for i, lbl in enumerate(labels.tolist()):
            if lbl != -1:
                by_label[int(lbl)].append(i)

        clusters: list[FailureCluster] = []
        for cluster_label, indices in sorted(by_label.items()):
            member_contexts = [contexts[i] for i in indices]
            description = self._labeler.label(member_contexts[:3])
            representative_idx = self._medoid(X, indices)

            clusters.append(
                FailureCluster(
                    label=f"cluster-{cluster_label}",
                    description=description,
                    trace_ids=[failures[i].id for i in indices],
                    size=len(indices),
                    representative_trace_id=failures[representative_idx].id,
                )
            )

        return clusters

    @staticmethod
    def _medoid(X: NDArray[np.float32], indices: list[int]) -> int:
        """Return the index (into the full X matrix) closest to the cluster centroid."""
        cluster_X = X[indices]
        centroid = cluster_X.mean(axis=0)
        dists: NDArray[Any] = np.linalg.norm(cluster_X - centroid, axis=1)
        return indices[int(dists.argmin())]
