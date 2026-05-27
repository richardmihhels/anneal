import { readFileSync } from "fs";
import { join } from "path";
import type {
  EvalResult,
  EvalScorePoint,
  GateSummary,
  OptimizationRun,
  ProposedChange,
  ProposedChangeWithEval,
  RunDetail,
  RunEvent,
  RunSummary,
  SeedData,
} from "./types";

function getData(): SeedData {
  const filePath = join(process.cwd(), "data", "seed.json");
  return JSON.parse(readFileSync(filePath, "utf-8")) as SeedData;
}

function numberFromMetadata(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function eventsForRun(events: RunEvent[], runId: string): RunEvent[] {
  return events
    .filter((event) => event.run_id === runId)
    .sort((a, b) => a.ts.localeCompare(b.ts));
}

function summarizeGate(run: OptimizationRun, events: RunEvent[]): GateSummary {
  const optimizationDone = events.find(
    (event) => event.stage === "optimization" && event.event === "completed",
  );
  const publishingDone = events.find(
    (event) => event.stage === "publishing" && event.event === "completed",
  );

  return {
    survivors:
      numberFromMetadata(optimizationDone?.metadata.survivors) ??
      run.proposed_change_ids.length,
    rejected:
      numberFromMetadata(optimizationDone?.metadata.rejected) ??
      Math.max(0, run.cluster_ids.length - run.proposed_change_ids.length),
    holdout_size:
      numberFromMetadata(optimizationDone?.metadata.holdout_size) ?? null,
    prs_opened:
      numberFromMetadata(publishingDone?.metadata.prs_opened) ??
      run.proposed_change_ids.length,
  };
}

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function evalsForRun(
  runId: string,
  proposedChanges: ProposedChange[],
  evalById: Map<string, EvalResult>,
): EvalResult[] {
  return proposedChanges
    .filter((change) => change.optimization_run_id === runId)
    .map((change) =>
      change.eval_result_id ? (evalById.get(change.eval_result_id) ?? null) : null,
    )
    .filter((evalResult): evalResult is EvalResult => evalResult !== null);
}

function detailForRun(run: OptimizationRun, data: SeedData): RunDetail {
  const events = eventsForRun(data.events, run.id);
  const evalById = new Map<string, EvalResult>(
    data.eval_results.map((evalResult) => [evalResult.id, evalResult]),
  );
  const proposedChanges: ProposedChangeWithEval[] = data.proposed_changes
    .filter((change) => change.optimization_run_id === run.id)
    .map((change) => ({
      ...change,
      eval_result: change.eval_result_id
        ? (evalById.get(change.eval_result_id) ?? null)
        : null,
    }));
  const publishingDone = events.find(
    (event) => event.stage === "publishing" && event.event === "completed",
  );
  const silenceRaw = publishingDone?.metadata.silence;

  return {
    ...run,
    events,
    clusters: data.clusters.filter((cluster) =>
      run.cluster_ids.includes(cluster.id),
    ),
    proposed_changes: proposedChanges,
    silence_report:
      typeof silenceRaw === "string" && silenceRaw.length > 0
        ? silenceRaw
        : null,
    gate: summarizeGate(run, events),
  };
}

export function listRuns(): RunSummary[] {
  const data = getData();
  const evalById = new Map<string, EvalResult>(
    data.eval_results.map((evalResult) => [evalResult.id, evalResult]),
  );

  return data.runs
    .slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .map((run) => {
      const events = eventsForRun(data.events, run.id);
      const gate = summarizeGate(run, events);
      const runEvals = evalsForRun(run.id, data.proposed_changes, evalById);

      return {
        ...run,
        prs_opened: gate.prs_opened,
        clusters_found: run.cluster_ids.length,
        gate,
        average_eval_delta: average(
          runEvals.map((evalResult) => evalResult.delta),
        ),
      };
    });
}

export function listRunDetails(): RunDetail[] {
  const data = getData();
  return data.runs
    .slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .map((run) => detailForRun(run, data));
}

export function getRun(id: string): RunDetail | null {
  const data = getData();
  const run = data.runs.find((candidate) => candidate.id === id);
  return run ? detailForRun(run, data) : null;
}

export function getOverviewStats(): {
  totalRuns: number;
  prsShipped: number;
  clustersFound: number;
  rejectionsPreventedByGate: number;
  weeklyActivity: { date: string; clusters: number; prs: number }[];
  evalScoreTrend: EvalScorePoint[];
  latestEvalScore: number | null;
} {
  const data = getData();
  const evalById = new Map<string, EvalResult>(
    data.eval_results.map((evalResult) => [evalResult.id, evalResult]),
  );
  const sortedRuns = data.runs
    .slice()
    .sort((a, b) => a.created_at.localeCompare(b.created_at));

  let prsShipped = 0;
  let clustersFound = 0;
  let rejectionsPreventedByGate = 0;
  const weeklyActivity: { date: string; clusters: number; prs: number }[] = [];
  const evalScoreTrend: EvalScorePoint[] = [];

  for (const run of sortedRuns) {
    const events = eventsForRun(data.events, run.id);
    const gate = summarizeGate(run, events);
    const runEvals = evalsForRun(run.id, data.proposed_changes, evalById);
    const date = run.created_at.slice(0, 10);

    prsShipped += gate.prs_opened;
    clustersFound += run.cluster_ids.length;
    rejectionsPreventedByGate += gate.rejected;

    weeklyActivity.push({
      date,
      clusters: run.cluster_ids.length,
      prs: gate.prs_opened,
    });

    evalScoreTrend.push({
      date,
      baseline_score: average(
        runEvals.map((evalResult) => evalResult.baseline_score),
      ),
      candidate_score: average(
        runEvals.map((evalResult) => evalResult.candidate_score),
      ),
      delta: average(runEvals.map((evalResult) => evalResult.delta)),
      prs: gate.prs_opened,
      rejected: gate.rejected,
    });
  }

  const latestEvalScore =
    evalScoreTrend
      .slice()
      .reverse()
      .find((point) => point.candidate_score !== null)?.candidate_score ?? null;

  return {
    totalRuns: data.runs.length,
    prsShipped,
    clustersFound,
    rejectionsPreventedByGate,
    weeklyActivity,
    evalScoreTrend,
    latestEvalScore,
  };
}
