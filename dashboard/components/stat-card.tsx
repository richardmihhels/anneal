import { Sparkline } from "./sparkline";

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  sparkPoints?: number[];
  accent?: "emerald" | "blue" | "zinc";
}

const accentColors = {
  emerald: "text-emerald-400",
  blue: "text-blue-400",
  zinc: "text-zinc-300",
};

export function StatCard({
  label,
  value,
  sub,
  sparkPoints,
  accent = "zinc",
}: Props) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4">
      <p className="text-xs text-zinc-500 uppercase tracking-wider">{label}</p>
      <div className="mt-2 flex items-end justify-between gap-3">
        <div>
          <p
            className={[
              "text-3xl font-semibold tabular-nums leading-none",
              accentColors[accent],
            ].join(" ")}
          >
            {value}
          </p>
          {sub && <p className="mt-1.5 text-xs text-zinc-600">{sub}</p>}
        </div>
        {sparkPoints && sparkPoints.length > 1 && (
          <div className={accentColors[accent]}>
            <Sparkline points={sparkPoints} width={80} height={28} />
          </div>
        )}
      </div>
    </div>
  );
}
