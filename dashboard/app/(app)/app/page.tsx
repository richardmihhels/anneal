import { AlarmBanner } from "@/components/alarm-banner";
import { CategoryBreakdown } from "@/components/category-breakdown";
import { EvalScoreTrend } from "@/components/eval-score-trend";
import { StatCard } from "@/components/stat-card";
import { getHealthData } from "@/lib/data";
import { requireSession } from "@/lib/auth";
import type { EvalScorePoint } from "@/lib/types";
import type { HealthEvalPoint } from "@/lib/types";

function healthEvalToScorePoint(p: HealthEvalPoint): EvalScorePoint {
  return {
    date: p.date,
    baseline_score: p.baseline_score,
    candidate_score: p.candidate_score,
    delta:
      p.baseline_score !== null && p.candidate_score !== null
        ? p.candidate_score - p.baseline_score
        : null,
    prs: p.prs_shipped,
    rejected: 0,
  };
}

function StatusBadge({ alarmCount }: { alarmCount: number }) {
  if (alarmCount > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-300">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" aria-hidden="true" />
        {alarmCount} alarm{alarmCount !== 1 ? "s" : ""} active
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-0.5 text-xs font-medium text-emerald-400">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
      Stable
    </span>
  );
}

function percent(value: number | null | undefined): string {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function signedPoints(value: number | null): string {
  if (value === null) return "—";
  const points = Math.round(value * 100);
  if (points === 0) return "0 pts";
  return `${points > 0 ? "+" : ""}${points} pts`;
}

function scoredPoints(
  points: HealthEvalPoint[],
): (HealthEvalPoint & { candidate_score: number })[] {
  return points.filter(
    (point): point is HealthEvalPoint & { candidate_score: number } =>
      point.candidate_score !== null,
  );
}

function largestCurrentCategory(
  points: { date: string; category: string; size: number }[],
): { category: string; size: number } | null {
  const dates = [...new Set(points.map((point) => point.date))].sort();
  const latestDate = dates[dates.length - 1];
  if (!latestDate) return null;
  return (
    points
      .filter((point) => point.date === latestDate)
      .sort((a, b) => b.size - a.size)[0] ?? null
  );
}

export default async function HealthPage() {
  const session = await requireSession();
  const health = await getHealthData(session.organizationId);
  const scorePoints = health.evalTrend.map(healthEvalToScorePoint);
  const scored = scoredPoints(health.evalTrend);
  const latestScore = scored[scored.length - 1] ?? null;
  const previousScore = scored[scored.length - 2] ?? null;
  const scoreDelta =
    latestScore && previousScore
      ? latestScore.candidate_score - previousScore.candidate_score
      : null;
  const evalSpark = scored.map((point) => point.candidate_score);
  const topCategory = largestCurrentCategory(health.categoryTrend);

  return (
    <div className="max-w-7xl">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-3">
            <h1 className="text-xl font-semibold text-zinc-100">Agent Health</h1>
            <StatusBadge alarmCount={health.activeAlarms.length} />
          </div>
          <p className="text-sm text-zinc-500">
            {health.agentId} &nbsp;·&nbsp; last {health.totalWeeks} weeks
          </p>
        </div>
        <div className="hidden text-right text-xs text-zinc-600 lg:block">
          <p>Daily assurance view</p>
          <p className="mt-1 text-zinc-500">holdout evals, clusters, alarms</p>
        </div>
      </div>

      <AlarmBanner alarms={health.activeAlarms} />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Current score"
          value={percent(latestScore?.candidate_score)}
          sub={latestScore ? `latest holdout · ${latestScore.date}` : "no eval recorded"}
          sparkPoints={evalSpark}
          accent="emerald"
        />
        <StatCard
          label="Week over week"
          value={signedPoints(scoreDelta)}
          sub={previousScore ? `from ${previousScore.date}` : "no prior eval"}
          accent={scoreDelta !== null && scoreDelta < 0 ? "zinc" : "emerald"}
        />
        <StatCard
          label="Open alarms"
          value={health.activeAlarms.length}
          sub={
            health.activeAlarms.length > 0
              ? "requires review"
              : "no active regressions"
          }
          accent={health.activeAlarms.length > 0 ? "blue" : "emerald"}
        />
        <StatCard
          label="Largest category"
          value={topCategory ? topCategory.size : "—"}
          sub={topCategory ? topCategory.category : "no current clusters"}
          accent="blue"
        />
      </div>

      <div className="mb-6 grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(340px,0.8fr)]">
        <EvalScoreTrend points={scorePoints} />
        <section
          aria-labelledby="readout-heading"
          className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4"
        >
          <p
            id="readout-heading"
            className="text-xs font-medium uppercase tracking-wider text-zinc-500"
          >
            Operational readout
          </p>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex items-center justify-between gap-4 border-b border-zinc-800 pb-3">
              <dt className="text-zinc-600">Agent</dt>
              <dd className="font-mono text-xs text-zinc-300">{health.agentId}</dd>
            </div>
            <div className="flex items-center justify-between gap-4 border-b border-zinc-800 pb-3">
              <dt className="text-zinc-600">Latest eval</dt>
              <dd className="font-mono text-xs text-zinc-300">
                {percent(latestScore?.candidate_score)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 border-b border-zinc-800 pb-3">
              <dt className="text-zinc-600">Direction</dt>
              <dd
                className={[
                  "text-xs font-medium",
                  scoreDelta !== null && scoreDelta < 0
                    ? "text-amber-300"
                    : "text-emerald-400",
                ].join(" ")}
              >
                {scoreDelta === null
                  ? "Needs prior week"
                  : scoreDelta < -0.01
                    ? "Down"
                    : scoreDelta > 0.01
                      ? "Improving"
                      : "Stable"}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-zinc-600">Alarm posture</dt>
              <dd
                className={[
                  "text-xs font-medium",
                  health.activeAlarms.length > 0
                    ? "text-amber-300"
                    : "text-emerald-400",
                ].join(" ")}
              >
                {health.activeAlarms.length > 0 ? "Review spike" : "Clear"}
              </dd>
            </div>
          </dl>
          <p className="mt-5 text-xs leading-relaxed text-zinc-500">
            This is the desktop triage view: score direction first, alarms
            second, failure mix below. A no-PR week is healthy when the score
            is stable and the alarm posture is clear.
          </p>
        </section>
      </div>

      <CategoryBreakdown points={health.categoryTrend} />

      {health.activeAlarms.length === 0 && (
        <div className="mt-6 rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 text-emerald-400" aria-hidden="true">✓</span>
            <div>
              <p className="text-sm font-medium text-zinc-200">
                No regressions detected
              </p>
              <p className="mt-1 text-xs leading-relaxed text-zinc-500">
                Anneal monitors your agent every week. When a failure category
                spikes significantly you&rsquo;ll see an alarm here. Weeks
                without a PR are normal — they mean no prompt change cleared
                the p&nbsp;&lt;&nbsp;0.05 gate, which is the right call.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
