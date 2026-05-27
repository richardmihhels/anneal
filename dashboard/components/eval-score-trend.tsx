import type { EvalScorePoint } from "@/lib/types";

interface Props {
  points: EvalScorePoint[];
}

interface ChartPoint {
  date: string;
  x: number;
  candidateY: number | null;
  baselineY: number | null;
  candidateScore: number | null;
  baselineScore: number | null;
  prs: number;
  rejected: number;
}

function formatScore(score: number | null): string {
  return score === null ? "no eval" : `${Math.round(score * 100)}%`;
}

function formatDelta(delta: number | null): string {
  return delta === null ? "" : `+${Math.round(delta * 100)} pts`;
}

function buildPath(points: { x: number; y: number }[]): string {
  return points
    .map((point, index) =>
      `${index === 0 ? "M" : "L"}${point.x.toFixed(1)},${point.y.toFixed(1)}`,
    )
    .join(" ");
}

export function EvalScoreTrend({ points }: Props) {
  const width = 560;
  const height = 124;
  const chartTop = 8;
  const chartHeight = 72;
  const maxIndex = Math.max(points.length - 1, 1);

  const chartPoints: ChartPoint[] = points.map((point, index) => {
    const x = 12 + (index / maxIndex) * (width - 24);
    const y = (score: number | null) =>
      score === null ? null : chartTop + (1 - score) * chartHeight;

    return {
      date: point.date,
      x,
      candidateY: y(point.candidate_score),
      baselineY: y(point.baseline_score),
      candidateScore: point.candidate_score,
      baselineScore: point.baseline_score,
      prs: point.prs,
      rejected: point.rejected,
    };
  });

  const candidateLine = chartPoints
    .filter(
      (point): point is ChartPoint & { candidateY: number } =>
        point.candidateY !== null,
    )
    .map((point) => ({ x: point.x, y: point.candidateY }));
  const baselineLine = chartPoints
    .filter(
      (point): point is ChartPoint & { baselineY: number } =>
        point.baselineY !== null,
    )
    .map((point) => ({ x: point.x, y: point.baselineY }));

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4">
      <div className="mb-3 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
            Eval-score trend
          </p>
          <p className="mt-1 text-xs text-zinc-600">
            Holdout candidate score after the weekly gate.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-600">
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Candidate
          </span>
          <span className="flex items-center gap-1">
            <span className="h-px w-3 bg-zinc-600" />
            Baseline
          </span>
        </div>
      </div>

      <svg
        role="img"
        aria-label="Eval score trend"
        viewBox={`0 0 ${width} ${height}`}
        className="h-36 w-full overflow-visible text-zinc-700"
      >
        <line
          x1="12"
          x2={width - 12}
          y1={chartTop}
          y2={chartTop}
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.35"
        />
        <line
          x1="12"
          x2={width - 12}
          y1={chartTop + chartHeight}
          y2={chartTop + chartHeight}
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.35"
        />
        {baselineLine.length > 1 && (
          <path
            d={buildPath(baselineLine)}
            fill="none"
            stroke="currentColor"
            strokeWidth="1.25"
            strokeDasharray="3 4"
          />
        )}
        {candidateLine.length > 1 && (
          <path
            d={buildPath(candidateLine)}
            fill="none"
            stroke="rgb(52 211 153)"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
          />
        )}
        {chartPoints.map((point) => (
          <g key={point.date}>
            {point.candidateY !== null ? (
              <circle
                cx={point.x}
                cy={point.candidateY}
                r="3"
                fill="rgb(52 211 153)"
              >
                <title>{`${point.date}: candidate ${formatScore(point.candidateScore)}, baseline ${formatScore(point.baselineScore)}`}</title>
              </circle>
            ) : (
              <circle
                cx={point.x}
                cy={chartTop + chartHeight}
                r="2"
                fill="rgb(63 63 70)"
              >
                <title>{`${point.date}: ${point.rejected > 0 ? "held by gate" : "quiet"}`}</title>
              </circle>
            )}
            <text
              x={point.x}
              y={height - 24}
              textAnchor="middle"
              className="fill-zinc-700 text-[10px]"
            >
              {point.date.slice(5)}
            </text>
            <text
              x={point.x}
              y={height - 9}
              textAnchor="middle"
              className="fill-zinc-500 text-[10px]"
            >
              {formatScore(point.candidateScore)}
            </text>
          </g>
        ))}
      </svg>

      <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-zinc-600 sm:grid-cols-4">
        {points.slice(-4).map((point) => (
          <div key={point.date} className="rounded border border-zinc-800 px-2 py-1.5">
            <div className="flex items-center justify-between gap-2">
              <span>{point.date.slice(5)}</span>
              <span className="font-mono text-zinc-400">
                {formatScore(point.candidate_score)}
              </span>
            </div>
            <div className="mt-0.5 text-[11px] text-zinc-700">
              {point.candidate_score === null
                ? point.rejected > 0
                  ? `${point.rejected} held`
                  : "quiet"
                : `${point.prs} shipped ${formatDelta(point.delta)}`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
