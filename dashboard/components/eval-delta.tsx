import type { EvalResult } from "@/lib/types";

interface Props {
  eval_result: EvalResult;
  compact?: boolean;
}

function formatP(p: number): string {
  if (p < 0.001) return "p<0.001";
  return `p=${p.toFixed(3)}`;
}

export function EvalDelta({ eval_result, compact = false }: Props) {
  const deltaPct = Math.round(eval_result.delta * 100);
  const baselinePct = Math.round(eval_result.baseline_score * 100);
  const candidatePct = Math.round(eval_result.candidate_score * 100);

  if (compact) {
    return (
      <span className="inline-flex items-center gap-1 font-mono text-xs text-emerald-400">
        +{deltaPct}%
        <span className="text-zinc-600">{formatP(eval_result.p_value)}</span>
      </span>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm font-semibold text-emerald-400">
          +{deltaPct}%
        </span>
        <span className="text-xs text-zinc-500">
          {baselinePct}% → {candidatePct}%
        </span>
        <span className="font-mono text-xs text-zinc-600">
          {formatP(eval_result.p_value)}, n={eval_result.sample_size}
        </span>
      </div>
      <div className="text-xs text-zinc-600">
        judge agreement {Math.round(eval_result.judge_agreement_rate * 100)}%
      </div>
    </div>
  );
}

export function RejectedDelta({ reason }: { reason?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-xs text-zinc-600">
        ✗ rejected — {reason ?? "did not beat baseline (p ≥ 0.05)"}
      </span>
    </div>
  );
}
