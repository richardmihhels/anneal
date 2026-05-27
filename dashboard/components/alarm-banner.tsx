import type { Alarm } from "@/lib/types";

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const h = Math.floor(ms / 3_600_000);
  if (h < 1) return "just now";
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export function AlarmBanner({ alarms }: { alarms: Alarm[] }) {
  if (alarms.length === 0) return null;

  return (
    <div
      role="alert"
      aria-label="Active regression alarms"
      className="mb-6 space-y-2"
    >
      {alarms.map((alarm) => (
        <div
          key={alarm.id}
          className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <span
                className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber-400"
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-medium text-amber-300">
                  {alarm.category} spike detected
                </p>
                <p className="mt-0.5 text-xs text-zinc-400">
                  Rate rose from{" "}
                  <span className="font-mono">{(alarm.baseline_rate * 100).toFixed(1)}%</span>{" "}
                  to{" "}
                  <span className="font-mono text-amber-300">
                    {(alarm.current_rate * 100).toFixed(1)}%
                  </span>{" "}
                  over the last {alarm.window_hours}h &mdash;{" "}
                  {alarm.affected_trace_count} conversation
                  {alarm.affected_trace_count !== 1 ? "s" : ""} affected
                </p>
                <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
                  {alarm.cause_hypothesis}
                </p>
              </div>
            </div>
            <span className="shrink-0 text-xs text-zinc-600">
              {relativeTime(alarm.first_detected)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
