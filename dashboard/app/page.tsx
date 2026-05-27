import Link from "next/link";
import { EvalScoreTrend } from "@/components/eval-score-trend";
import { getOverviewStats, listRuns } from "@/lib/data";
import { StatCard } from "@/components/stat-card";
import { RunStatusBadge } from "@/components/run-status-badge";
import { requireSession } from "@/lib/auth";

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const days = Math.floor(ms / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  return `${days}d ago`;
}

function WeeklyChart({
  data,
}: {
  data: { date: string; clusters: number; prs: number }[];
}) {
  const maxClusters = Math.max(...data.map((d) => d.clusters), 1);
  return (
    <div className="flex h-16 items-end gap-1.5">
      {data.map((week) => (
        <div
          key={week.date}
          className="flex flex-1 flex-col items-center gap-0.5"
          title={`${week.date}: ${week.clusters} clusters, ${week.prs} PRs`}
        >
          <div
            className="flex w-full flex-col justify-end"
            style={{ height: "52px" }}
          >
            <div
              className="relative w-full overflow-hidden rounded-sm bg-zinc-700"
              style={{
                height: `${Math.max(3, (week.clusters / maxClusters) * 52)}px`,
              }}
            >
              {week.prs > 0 && (
                <div
                  className="absolute bottom-0 left-0 right-0 bg-indigo-500/60"
                  style={{
                    height: `${(week.prs / Math.max(week.clusters, 1)) * 100}%`,
                  }}
                />
              )}
            </div>
          </div>
          <span className="text-zinc-700" style={{ fontSize: "9px" }}>
            {week.date.slice(5)}
          </span>
        </div>
      ))}
    </div>
  );
}

function percent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export default async function OverviewPage() {
  const session = await requireSession();
  const stats = getOverviewStats(session.organizationId);
  const runs = listRuns(session.organizationId).slice(0, 5);
  const sparkPrs = stats.weeklyActivity.map((w) => w.prs);
  const evalSpark = stats.evalScoreTrend
    .map((point) => point.candidate_score)
    .filter((score): score is number => score !== null);

  return (
    <div className="max-w-5xl">
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-zinc-100">Overview</h1>
        <p className="mt-1 text-sm text-zinc-500">
          {session.organizationName} &nbsp;·&nbsp; last {stats.totalRuns} weeks
        </p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Latest eval score"
          value={percent(stats.latestEvalScore)}
          sub="holdout candidate score"
          sparkPoints={evalSpark}
          accent="emerald"
        />
        <StatCard
          label="PRs shipped"
          value={stats.prsShipped}
          sub={`across ${stats.totalRuns} weekly runs`}
          sparkPoints={sparkPrs}
          accent="emerald"
        />
        <StatCard
          label="Regressions prevented"
          value={stats.rejectionsPreventedByGate}
          sub="candidates that failed p < 0.05 gate"
          accent="zinc"
        />
        <StatCard
          label="Failure clusters"
          value={stats.clustersFound}
          sub="patterns grouped for eval"
          accent="blue"
        />
      </div>

      <div className="mb-8 grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <EvalScoreTrend points={stats.evalScoreTrend} />
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4">
          <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
            Weekly activity
          </p>
          <WeeklyChart data={stats.weeklyActivity} />
          <p className="mt-3 text-xs text-zinc-600">
            Grey bars are clustered failures. Indigo fill is PRs shipped after
            the eval gate.
          </p>
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs uppercase tracking-wider text-zinc-500">
            Recent runs
          </p>
          <Link
            href="/runs"
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            View all →
          </Link>
        </div>

        <div className="rounded-lg border border-zinc-800 divide-y divide-zinc-800">
          {runs.map((run) => (
            <Link
              key={run.id}
              href={`/runs/${run.id}`}
              className="group flex items-center justify-between px-4 py-3 transition-colors hover:bg-zinc-900/60"
            >
              <div className="flex items-center gap-3">
                <RunStatusBadge status={run.status} size="sm" />
                <span className="font-mono text-xs text-zinc-300">
                  {run.id.slice(0, 8)}
                </span>
                {run.prs_opened > 0 && (
                  <span className="text-xs text-emerald-500">
                    {run.prs_opened} PR{run.prs_opened !== 1 ? "s" : ""} opened
                  </span>
                )}
                {run.clusters_found > 0 &&
                  run.prs_opened === 0 &&
                  run.status === "completed" && (
                    <span className="text-xs text-zinc-600">
                      {run.clusters_found} clusters, nothing shipped
                    </span>
                  )}
              </div>
              <span className="text-xs text-zinc-600 group-hover:text-zinc-400 transition-colors">
                {relativeTime(run.created_at)}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
