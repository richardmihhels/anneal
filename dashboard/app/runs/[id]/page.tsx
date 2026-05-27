import Link from "next/link";
import { notFound } from "next/navigation";
import { getRun } from "@/lib/data";
import { RunStatusBadge } from "@/components/run-status-badge";
import { EvalDelta } from "@/components/eval-delta";
import { EmptyState } from "@/components/empty-state";
import { RunEventsTimeline } from "@/components/run-events-timeline";
import { requireSession } from "@/lib/auth";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function formatDelta(delta: number | null): string {
  return delta === null ? "—" : `+${Math.round(delta * 100)} pts`;
}

function extractExcerpt(rationale: string): string {
  for (const line of rationale.split("\n")) {
    if (line.startsWith("> ")) return line.slice(2).trim();
  }
  return "";
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function RunDetailPage({ params }: PageProps) {
  const session = await requireSession();
  const { id } = await params;
  const run = getRun(id, session.organizationId);
  if (!run) notFound();

  const isFailed = run.status === "failed";
  const isSkipped =
    run.cluster_ids.length === 0 &&
    run.status === "completed" &&
    run.events.some((e) => e.event === "info" && e.message.includes("Not enough traces"));
  const hasNoClusters =
    !isFailed &&
    !isSkipped &&
    run.clusters.length === 0;
  const hasClusters = run.clusters.length > 0;
  const hasChanges = run.proposed_changes.length > 0;
  const rejectedCount = run.gate.rejected;
  const candidateCount = run.gate.survivors + run.gate.rejected;
  const acceptedEvals = run.proposed_changes
    .map((change) => change.eval_result)
    .filter((evalResult) => evalResult !== null);
  const averageDelta =
    acceptedEvals.length > 0
      ? acceptedEvals.reduce((sum, evalResult) => sum + evalResult.delta, 0) /
        acceptedEvals.length
      : null;

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/runs"
          className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          ← Runs
        </Link>
        <div className="mt-3 flex items-center gap-3">
          <RunStatusBadge status={run.status} />
          <span className="font-mono text-sm text-zinc-500">{run.id}</span>
          <span className="text-xs text-zinc-700">{formatDate(run.created_at)}</span>
        </div>
      </div>

      <section className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <GateMetric
          label="Candidates tried"
          value={candidateCount}
          sub={
            run.gate.holdout_size !== null
              ? `holdout n=${run.gate.holdout_size}`
              : "no holdout"
          }
        />
        <GateMetric
          label="Shipped"
          value={run.gate.prs_opened}
          sub="opened as PRs"
          tone="good"
        />
        <GateMetric
          label="Rejected"
          value={rejectedCount}
          sub="held by gate"
        />
        <GateMetric
          label="Eval delta"
          value={formatDelta(averageDelta)}
          sub="avg survivor"
          tone={averageDelta !== null ? "good" : "muted"}
        />
      </section>

      {/* Stage timeline */}
      <section className="mb-8 rounded-lg border border-zinc-800 bg-zinc-900/30 px-5 py-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
          Pipeline timeline
        </p>
        <RunEventsTimeline events={run.events} />
      </section>

      {/* Status-specific states */}
      {isFailed && (
        <div className="mb-6">
          <EmptyState kind="failed" />
        </div>
      )}
      {isSkipped && (
        <div className="mb-6">
          <EmptyState kind="too-few-traces" />
        </div>
      )}
      {hasNoClusters && (
        <div className="mb-6">
          <EmptyState kind="no-clusters" />
        </div>
      )}

      {/* Failure clusters */}
      {hasClusters && (
        <section className="mb-8">
          <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
            Failure clusters ({run.clusters.length})
          </p>
          <div className="space-y-2">
            {run.clusters.map((cluster) => (
              <div
                key={cluster.id}
                className="rounded-lg border border-zinc-800 bg-zinc-900/30 px-4 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-zinc-200">
                      {cluster.description}
                    </p>
                    <p className="mt-0.5 text-xs text-zinc-500">
                      {cluster.size} trace{cluster.size !== 1 ? "s" : ""} &nbsp;·&nbsp;{" "}
                      <span className="font-mono text-zinc-600">{cluster.label}</span>
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Proposed changes (shipped) */}
      {hasChanges && (
        <section className="mb-8">
          <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
            Candidates shipped ({run.proposed_changes.length})
          </p>
          <div className="space-y-3">
            {run.proposed_changes.map((change) => {
              const ev = change.eval_result;
              const excerpt = extractExcerpt(change.rationale);
              return (
                <div
                  key={change.id}
                  className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-4"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs font-semibold text-emerald-400">
                      ✓ SHIPPED
                    </span>
                    {ev && <EvalDelta eval_result={ev} compact />}
                  </div>

                  {excerpt && (
                    <blockquote className="mb-3 border-l-2 border-zinc-700 pl-3 text-xs italic text-zinc-500">
                      {truncate(excerpt, 200)}
                    </blockquote>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="mb-1 text-xs text-zinc-600 uppercase tracking-wide">
                        Before
                      </p>
                      <pre className="rounded bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-400 whitespace-pre-wrap break-all">
                        {truncate(change.before, 300)}
                      </pre>
                    </div>
                    <div>
                      <p className="mb-1 text-xs text-zinc-600 uppercase tracking-wide">
                        After
                      </p>
                      <pre className="rounded bg-zinc-950 px-3 py-2 font-mono text-xs text-emerald-400/80 whitespace-pre-wrap break-all">
                        {truncate(change.after, 300)}
                      </pre>
                    </div>
                  </div>

                  {ev && (
                    <div className="mt-3 border-t border-emerald-500/10 pt-3">
                      <p className="mb-2 text-xs text-zinc-500">
                        Why shipped: the candidate beat the baseline on the
                        holdout eval and passed the statistical gate.
                      </p>
                      <EvalDelta eval_result={ev} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Silent state when clusters were found but nothing shipped */}
      {hasClusters && !hasChanges && !isFailed && (
        <EmptyState
          kind="no-survivors"
          clusterCount={run.clusters.length}
          rejectedCount={rejectedCount}
          silenceReport={run.silence_report}
        />
      )}

      {/* Rejection summary if some clusters had no survivor */}
      {hasChanges && rejectedCount > 0 && (
        <section className="mb-8">
          <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
            Candidates rejected ({rejectedCount})
          </p>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 px-4 py-3">
            <p className="text-xs text-zinc-500">
              {rejectedCount} cluster
              {rejectedCount !== 1 ? "s" : ""} were evaluated but no
              candidate beat the baseline with p&nbsp;&lt;&nbsp;0.05. No change
              was shipped for these patterns — the gate prevented a noisy update.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}

function GateMetric({
  label,
  value,
  sub,
  tone = "muted",
}: {
  label: string;
  value: string | number;
  sub: string;
  tone?: "good" | "muted";
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 px-4 py-3">
      <p className="text-[11px] uppercase tracking-wider text-zinc-600">
        {label}
      </p>
      <p
        className={[
          "mt-1 font-mono text-lg font-semibold",
          tone === "good" ? "text-emerald-400" : "text-zinc-200",
        ].join(" ")}
      >
        {value}
      </p>
      <p className="mt-0.5 text-xs text-zinc-600">{sub}</p>
    </div>
  );
}
