export type RunStatus = "pending" | "running" | "completed" | "failed";
export type RunStage = "init" | "clustering" | "optimization" | "publishing" | "done";
export type RunEventKind = "started" | "completed" | "failed" | "info";

export interface OptimizationRun {
  id: string;
  organization_id?: string;
  agent_id: string;
  created_at: string;
  status: RunStatus;
  cluster_ids: string[];
  proposed_change_ids: string[];
}

export interface RunEvent {
  id: string;
  run_id: string;
  stage: RunStage;
  event: RunEventKind;
  message: string;
  ts: string;
  metadata: Record<string, unknown>;
}

export interface FailureCluster {
  id: string;
  label: string;
  description: string;
  trace_ids: string[];
  size: number;
  created_at: string;
  representative_trace_id: string | null;
}

export interface ProposedChange {
  id: string;
  optimization_run_id: string;
  target: string;
  before: string;
  after: string;
  rationale: string;
  eval_result_id: string | null;
}

export interface EvalResult {
  id: string;
  proposed_change_id: string;
  run_at: string;
  baseline_score: number;
  candidate_score: number;
  delta: number;
  p_value: number;
  sample_size: number;
  passed: boolean;
  judge_agreement_rate: number;
}

export interface SeedData {
  runs: OptimizationRun[];
  events: RunEvent[];
  clusters: FailureCluster[];
  proposed_changes: ProposedChange[];
  eval_results: EvalResult[];
}

export interface ProposedChangeWithEval extends ProposedChange {
  eval_result: EvalResult | null;
}

export interface GateSummary {
  survivors: number;
  rejected: number;
  holdout_size: number | null;
  prs_opened: number;
}

export interface RunDetail extends OptimizationRun {
  events: RunEvent[];
  clusters: FailureCluster[];
  proposed_changes: ProposedChangeWithEval[];
  silence_report: string | null;
  gate: GateSummary;
}

export interface RunSummary extends OptimizationRun {
  prs_opened: number;
  clusters_found: number;
  gate: GateSummary;
  average_eval_delta: number | null;
}

export interface EvalScorePoint {
  date: string;
  baseline_score: number | null;
  candidate_score: number | null;
  delta: number | null;
  prs: number;
  rejected: number;
}
