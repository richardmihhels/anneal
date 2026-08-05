import Link from "next/link";
import { EvalDelta } from "@/components/eval-delta";
import { RunStatusBadge } from "@/components/run-status-badge";
import type { RunDetail } from "@/lib/types";

interface Props {
  runs: RunDetail[];
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function outcome(run: RunDetail): { label: string; className: string } {
  if (run.status === "failed") {
    return { label: "failed before publish", className: "text-red-400" };
  }
  if (run.gate.prs_opened > 0) {
    return {
      label: `${run.gate.prs_opened} shipped`,
      className: "text-emerald-400",
    };
  }
  if (run.gate.rejected > 0) {
    return { label: `${run.gate.rejected} held`, className: "text-zinc-500" };
  }
  return { label: "quiet", className: "text-zinc-600" };
}

export function RunsTimeline({ runs }: Props) {
  return (
    <div className="relative">
      <div className="absolute bottom-4 left-[9px] top-4 w-px bg-zinc-800" />
      <div className="space-y-2">
        {runs.map((run) => {
          const runOutcome = outcome(run);
          return (
            <details
              key={run.id}
              className="group relative rounded-lg border border-zinc-800 bg-zinc-950/40 open:bg-zinc-900/40"
            >
              <summary className="grid cursor-pointer list-none grid-cols-[18px_1fr_auto] items-center gap-3 px-4 py-3 marker:hidden">
                <span className="relative z-[1] h-2.5 w-2.5 rounded-full border border-zinc-950 bg-zinc-600 group-open:bg-zinc-300" />
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <RunStatusBadge status={run.status} size="sm" />
                    <span className="font-mono text-xs text-zinc-400">
                      {run.id.slice(0, 12)}
                    </span>
                    <span className="text-xs text-zinc-600">
                      {formatDate(run.created_at)}
                    </span>
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500">
                    <span>{run.clusters.length} clusters</span>
                    <span>{run.proposed_changes.length} candidates passed</span>
                    {run.gate.holdout_size !== null && (
                      <span>holdout n={run.gate.holdout_size}</span>
                    )}
                  </span>
                </span>
                <span
                  className={[
                    "justify-self-end text-xs font-medium",
                    runOutcome.className,
                  ].join(" ")}
                >
                  {runOutcome.label}
                </span>
              </summary>

              <div className="border-t border-zinc-800 px-4 py-4">
                <div className="grid gap-4 lg:grid-cols-2">
                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                        Clusters
                      </p>
                      <span className="text-xs text-zinc-700">
                        {run.clusters.length || "none"}
                      </span>
                    </div>
                    {run.clusters.length > 0 ? (
                      <div className="max-h-56 space-y-1.5 overflow-y-auto pr-1">
                        {run.clusters.map((cluster) => (
                          <div
                            key={cluster.id}
                            className="rounded border border-zinc-800 px-3 py-2"
                          >
                            <p className="truncate text-xs font-medium text-zinc-300">
                              {cluster.description}
                            </p>
                            <p className="mt-0.5 text-[11px] text-zinc-600">
                              {cluster.size} traces · {cluster.label}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="rounded border border-zinc-800 px-3 py-3 text-xs text-zinc-600">
                        No failure cluster crossed the threshold for this run.
                      </p>
                    )}
                  </div>

                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                        Candidates
                      </p>
                      <span className="text-xs text-zinc-700">
                        {run.gate.prs_opened} published / {run.gate.survivors} passed /{" "}
                        {run.gate.rejected} rejected
                      </span>
                    </div>
                    {run.proposed_changes.length > 0 ? (
                      <div className="max-h-56 space-y-1.5 overflow-y-auto pr-1">
                        {run.proposed_changes.map((change) => (
                          <div
                            key={change.id}
                            className={[
                              "rounded border px-3 py-2",
                              change.published
                                ? "border-emerald-500/20 bg-emerald-500/5"
                                : "border-zinc-800 bg-zinc-950/30",
                            ].join(" ")}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-mono text-[11px] text-zinc-500">
                                {change.id.slice(0, 8)}
                              </span>
                              {change.eval_result && (
                                <EvalDelta eval_result={change.eval_result} compact />
                              )}
                            </div>
                            <p className="mt-1 text-xs text-zinc-500">
                              {change.published
                                ? "Published because it was the strongest holdout-gated improvement."
                                : "Passed the gate; held because another survivor was stronger."}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="rounded border border-zinc-800 px-3 py-3 text-xs leading-relaxed text-zinc-600">
                        {run.gate.rejected > 0
                          ? `${run.gate.rejected} candidate patterns were held because none beat the baseline with p < 0.05.`
                          : "No candidate was needed; Anneal stayed quiet."}
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-4 flex justify-end">
                  <Link
                    href={`/runs/${run.id}`}
                    className="text-xs text-zinc-500 transition-colors hover:text-zinc-200"
                  >
                    Open run detail
                  </Link>
                </div>
              </div>
            </details>
          );
        })}
      </div>
    </div>
  );
}
