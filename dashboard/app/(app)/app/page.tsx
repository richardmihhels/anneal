import { AlarmBanner } from "@/components/alarm-banner";
import { CategoryBreakdown } from "@/components/category-breakdown";
import { EvalScoreTrend } from "@/components/eval-score-trend";
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

export default async function HealthPage() {
  const session = await requireSession();
  const health = getHealthData(session.organizationId);
  const scorePoints = health.evalTrend.map(healthEvalToScorePoint);

  return (
    <div className="max-w-5xl">
      <div className="mb-8">
        <div className="mb-2 flex items-center gap-3">
          <h1 className="text-xl font-semibold text-zinc-100">Agent Health</h1>
          <StatusBadge alarmCount={health.activeAlarms.length} />
        </div>
        <p className="text-sm text-zinc-500">
          {health.agentId} &nbsp;·&nbsp; last {health.totalWeeks} weeks
        </p>
      </div>

      <AlarmBanner alarms={health.activeAlarms} />

      <div className="mb-6">
        <EvalScoreTrend points={scorePoints} />
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
