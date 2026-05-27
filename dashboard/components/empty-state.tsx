interface Props {
  kind: "no-clusters" | "no-survivors" | "too-few-traces" | "failed";
  clusterCount?: number;
  rejectedCount?: number;
  silenceReport?: string | null;
}

export function EmptyState({
  kind,
  clusterCount,
  rejectedCount,
  silenceReport,
}: Props) {
  if (kind === "failed") {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-6">
        <p className="text-sm font-medium text-red-400">Pipeline error</p>
        <p className="mt-1 text-xs text-zinc-500">
          This run encountered an error before completing. Check the event
          timeline below for details.
        </p>
      </div>
    );
  }

  if (kind === "too-few-traces") {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-6">
        <p className="text-sm font-medium text-zinc-300">Skipped — low traffic</p>
        <p className="mt-1 text-xs text-zinc-500">
          Fewer than 20 traces were available this cycle. Anneal requires a
          minimum sample to produce statistically valid clusters.
        </p>
      </div>
    );
  }

  if (kind === "no-clusters") {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-8 text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10">
          <span className="text-lg text-emerald-400">✓</span>
        </div>
        <p className="text-sm font-medium text-zinc-200">
          Agent performing well
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
          No failure patterns exceeded the minimum cluster size this week.
          Anneal found nothing worth fixing — which is a good outcome.
        </p>
      </div>
    );
  }

  // no-survivors
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-8 text-center">
      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800">
        <span className="text-base text-zinc-400">◦</span>
      </div>
      <p className="text-sm font-medium text-zinc-200">Nothing shipped this week</p>
      <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
        {silenceReport ??
          `${clusterCount ?? 0} cluster${(clusterCount ?? 0) !== 1 ? "s" : ""} analyzed, ${rejectedCount ?? 0} candidate${(rejectedCount ?? 0) !== 1 ? "s" : ""} evaluated — none passed the p < 0.05 gate. No update was shipped. This is the right call.`}
      </p>
    </div>
  );
}
