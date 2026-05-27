"use client";

import { useState } from "react";
import type { RunEvent, RunStage } from "@/lib/types";

const STAGE_ORDER: RunStage[] = [
  "init",
  "clustering",
  "optimization",
  "publishing",
  "done",
];

const STAGE_LABELS: Record<RunStage, string> = {
  init: "Init",
  clustering: "Cluster",
  optimization: "Optimize",
  publishing: "Publish",
  done: "Done",
};

function stageStatus(
  events: RunEvent[],
  stage: RunStage,
): "done" | "failed" | "active" | "pending" {
  const stageEvents = events.filter((e) => e.stage === stage);
  if (stageEvents.some((e) => e.event === "failed")) return "failed";
  if (stageEvents.some((e) => e.event === "completed")) return "done";
  if (stageEvents.some((e) => e.event === "started")) return "active";
  return "pending";
}

const dotStyle: Record<string, string> = {
  done: "bg-emerald-500",
  failed: "bg-red-500",
  active: "bg-blue-500 animate-pulse",
  pending: "bg-zinc-700",
};

const lineStyle: Record<string, string> = {
  done: "bg-emerald-500/40",
  failed: "bg-red-500/20",
  active: "bg-zinc-700",
  pending: "bg-zinc-800",
};

function formatTs(ts: string): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

interface Props {
  events: RunEvent[];
}

export function RunEventsTimeline({ events }: Props) {
  const [expanded, setExpanded] = useState(false);

  const relevantStages = STAGE_ORDER.filter((s) =>
    events.some((e) => e.stage === s),
  );

  return (
    <div>
      {/* Stage stepper */}
      <div className="flex items-center gap-0">
        {relevantStages.map((stage, i) => {
          const status = stageStatus(events, stage);
          return (
            <div key={stage} className="flex items-center">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={[
                    "h-2 w-2 rounded-full",
                    dotStyle[status],
                  ].join(" ")}
                />
                <span className="text-xs text-zinc-500">
                  {STAGE_LABELS[stage]}
                </span>
              </div>
              {i < relevantStages.length - 1 && (
                <div
                  className={[
                    "mb-4 h-px w-12",
                    lineStyle[status],
                  ].join(" ")}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Toggle */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="mt-3 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
      >
        {expanded ? "Hide" : "Show"} event log ({events.length} events)
      </button>

      {/* Full event log */}
      {expanded && (
        <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950 divide-y divide-zinc-800/50">
          {events.map((ev) => (
            <div key={ev.id} className="flex gap-3 px-4 py-2.5">
              <span className="shrink-0 font-mono text-xs text-zinc-700 tabular-nums">
                {formatTs(ev.ts)}
              </span>
              <span
                className={[
                  "shrink-0 text-xs font-medium",
                  ev.event === "failed"
                    ? "text-red-400"
                    : ev.event === "completed"
                      ? "text-emerald-400"
                      : ev.event === "info"
                        ? "text-yellow-400"
                        : "text-zinc-400",
                ].join(" ")}
              >
                {ev.stage}
              </span>
              <span className="text-xs text-zinc-400">{ev.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
