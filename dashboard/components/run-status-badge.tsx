import type { RunStatus } from "@/lib/types";

const styles: Record<RunStatus, string> = {
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  running: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
  pending: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

const labels: Record<RunStatus, string> = {
  completed: "Completed",
  running: "Running",
  failed: "Failed",
  pending: "Pending",
};

interface Props {
  status: RunStatus;
  size?: "sm" | "md";
}

export function RunStatusBadge({ status, size = "md" }: Props) {
  return (
    <span
      className={[
        "inline-flex items-center rounded border font-medium tabular-nums",
        size === "sm" ? "px-1.5 py-0.5 text-xs" : "px-2 py-0.5 text-xs",
        styles[status],
      ].join(" ")}
    >
      {labels[status]}
    </span>
  );
}
