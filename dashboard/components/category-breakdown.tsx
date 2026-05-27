import type { CategoryWeekPoint } from "@/lib/types";
import { Sparkline } from "./sparkline";

interface Props {
  points: CategoryWeekPoint[];
}

function buildCategorySeries(
  points: CategoryWeekPoint[],
): { category: string; sizes: number[]; peak: number; latest: number }[] {
  const allDates = [...new Set(points.map((p) => p.date))].sort();
  const byCategory = new Map<string, Map<string, number>>();

  for (const p of points) {
    const catMap = byCategory.get(p.category) ?? new Map<string, number>();
    catMap.set(p.date, (catMap.get(p.date) ?? 0) + p.size);
    byCategory.set(p.category, catMap);
  }

  return [...byCategory.entries()]
    .map(([category, dateMap]) => {
      const sizes = allDates.map((d) => dateMap.get(d) ?? 0);
      const nonZero = sizes.filter((s) => s > 0);
      return {
        category,
        sizes,
        peak: Math.max(...nonZero, 0),
        latest: sizes[sizes.length - 1] ?? 0,
      };
    })
    .sort((a, b) => b.peak - a.peak);
}

function trend(sizes: number[]): "up" | "down" | "flat" {
  const nonZero = sizes.filter((s) => s > 0);
  if (nonZero.length < 2) return "flat";
  const first = nonZero[0];
  const last = nonZero[nonZero.length - 1];
  if (last > first * 1.2) return "up";
  if (last < first * 0.8) return "down";
  return "flat";
}

const trendColors = {
  up: "text-red-400",
  down: "text-emerald-400",
  flat: "text-zinc-400",
};

const trendLabels = {
  up: "↑ rising",
  down: "↓ falling",
  flat: "→ stable",
};

export function CategoryBreakdown({ points }: Props) {
  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4">
        <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          Failure categories
        </p>
        <p className="mt-4 text-sm text-zinc-600">
          No failure clusters detected across monitored weeks.
        </p>
      </div>
    );
  }

  const series = buildCategorySeries(points);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4">
      <p className="mb-4 text-xs font-medium uppercase tracking-wider text-zinc-500">
        Failure categories
      </p>
      <p className="mb-4 text-xs text-zinc-600">
        Cluster size per week. Falling is good.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {series.map(({ category, sizes, latest }) => {
          const direction = trend(sizes);
          return (
            <div
              key={category}
              className="rounded border border-zinc-800 bg-zinc-900 px-3 py-2.5"
            >
              <div className="mb-2 flex items-start justify-between gap-2">
                <p className="text-xs font-medium leading-snug text-zinc-300">
                  {category}
                </p>
                <span
                  className={[
                    "shrink-0 text-[10px] font-medium",
                    trendColors[direction],
                  ].join(" ")}
                  aria-label={`Trend: ${trendLabels[direction]}`}
                >
                  {trendLabels[direction]}
                </span>
              </div>
              <div className="flex items-end justify-between gap-3">
                <div className={trendColors[direction]}>
                  <Sparkline points={sizes} width={90} height={28} />
                </div>
                <span className="font-mono text-xs text-zinc-500">
                  {latest > 0 ? `${latest} this wk` : "none"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
