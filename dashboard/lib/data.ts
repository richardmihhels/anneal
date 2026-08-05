import { readFileSync } from "fs";
import { join } from "path";
import type {
  Alarm,
  CategoryWeekPoint,
  EvalResult,
  EvalScorePoint,
  GateSummary,
  HealthEvalPoint,
  OptimizationRun,
  ProposedChange,
  ProposedChangeWithEval,
  RunDetail,
  RunEvent,
  RunSummary,
  SeedData,
  WeeklyDigest,
} from "./types";

const FALLBACK_ORG_ID = "org_demo";

async function getData(organizationId: string): Promise<SeedData> {
  const source = process.env.ANNEAL_DATA_SOURCE ?? "seed";
  if (source === "seed") {
    const filePath = join(process.cwd(), "data", "seed.json");
    const data = JSON.parse(readFileSync(filePath, "utf-8")) as SeedData;
    return scopedData(data, organizationId);
  }
  if (source !== "api") {
    throw new Error("ANNEAL_DATA_SOURCE must be either 'seed' or 'api'");
  }

  const endpoint = process.env.ANNEAL_ENDPOINT?.replace(/\/$/, "");
  if (!endpoint) {
    throw new Error("ANNEAL_ENDPOINT is required when ANNEAL_DATA_SOURCE=api");
  }
  const headers: Record<string, string> = { "X-Anneal-Org": organizationId };
  const apiKey = process.env.ANNEAL_API_KEY;
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;

  const response = await fetch(`${endpoint}/dashboard/data`, {
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Anneal API returned ${response.status} while loading dashboard data`);
  }
  return scopedData((await response.json()) as SeedData, organizationId);
}

function runOrgId(run: OptimizationRun): string {
  return run.organization_id ?? FALLBACK_ORG_ID;
}

function scopedData(data: SeedData, organizationId: string): SeedData {
  const runs = data.runs.filter((run) => runOrgId(run) === organizationId);
  const runIds = new Set(runs.map((run) => run.id));
  const events = data.events.filter((event) => runIds.has(event.run_id));
  const proposedChanges = data.proposed_changes.filter((change) =>
    runIds.has(change.optimization_run_id),
  );
  const changeIds = new Set(proposedChanges.map((change) => change.id));
  const clusterIds = new Set(runs.flatMap((run) => run.cluster_ids));

  return {
    runs,
    events,
    clusters: data.clusters.filter((cluster) => clusterIds.has(cluster.id)),
    proposed_changes: proposedChanges,
    eval_results: data.eval_results.filter(
      (evalResult) =>
        (evalResult.proposed_change_id != null &&
          changeIds.has(evalResult.proposed_change_id)) ||
        (evalResult.optimization_run_id != null &&
          runIds.has(evalResult.optimization_run_id)),
    ),
    alarms: (data.alarms ?? []).filter(
      (alarm) => alarm.organization_id === organizationId,
    ),
    weekly_digests: (data.weekly_digests ?? []).filter(
      (digest) => digest.organization_id === organizationId,
    ),
  };
}

function numberFromMetadata(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringArrayFromMetadata(value: unknown): string[] | null {
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : null;
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
      Math.min(run.proposed_change_ids.length, 1),
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
  const gate = summarizeGate(run, events);
  const evalById = new Map<string, EvalResult>(
    data.eval_results.map((evalResult) => [evalResult.id, evalResult]),
  );
  const changesWithEval = data.proposed_changes
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
  const publishedFromEvent = stringArrayFromMetadata(
    publishingDone?.metadata.published_change_ids,
  );
  const inferredPublishedIds = changesWithEval
    .slice()
    .sort(
      (a, b) =>
        (b.eval_result?.delta ?? Number.NEGATIVE_INFINITY) -
        (a.eval_result?.delta ?? Number.NEGATIVE_INFINITY),
    )
    .slice(0, gate.prs_opened)
    .map((change) => change.id);
  const publishedIds = new Set(publishedFromEvent ?? inferredPublishedIds);
  const proposedChanges: ProposedChangeWithEval[] = changesWithEval.map(
    (change) => ({
      ...change,
      published: publishedIds.has(change.id),
    }),
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
    gate,
  };
}

export async function listRuns(organizationId: string): Promise<RunSummary[]> {
  const data = await getData(organizationId);
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

export async function listRunDetails(organizationId: string): Promise<RunDetail[]> {
  const data = await getData(organizationId);
  return data.runs
    .slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .map((run) => detailForRun(run, data));
}

export async function getRun(id: string, organizationId: string): Promise<RunDetail | null> {
  const data = await getData(organizationId);
  const run = data.runs.find((candidate) => candidate.id === id);
  return run ? detailForRun(run, data) : null;
}

export async function getWeeklyDigest(
  id: string,
  organizationId: string,
): Promise<WeeklyDigest | null> {
  const data = await getData(organizationId);
  return data.weekly_digests?.find((digest) => digest.id === id) ?? null;
}

export async function getWeeklyDigestForRun(
  runId: string,
  organizationId: string,
): Promise<WeeklyDigest | null> {
  const data = await getData(organizationId);
  return (
    data.weekly_digests?.find((digest) => digest.optimization_run_id === runId) ??
    null
  );
}

export async function getOverviewStats(organizationId: string): Promise<{
  totalRuns: number;
  prsShipped: number;
  clustersFound: number;
  rejectionsPreventedByGate: number;
  weeklyActivity: { date: string; clusters: number; prs: number }[];
  evalScoreTrend: EvalScorePoint[];
  latestEvalScore: number | null;
}> {
  const data = await getData(organizationId);
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

function _normalizeCategory(description: string): string {
  const lower = description.toLowerCase();
  if (lower.includes("policy violation")) return "Policy violation";
  if (lower.includes("premature escalation")) return "Premature escalation";
  if (lower.includes("unresolved ticket")) return "Unresolved ticket";
  if (lower.includes("scope creep")) return "Scope creep";
  if (lower.includes("hallucinated")) return "Hallucinated policy";
  if (lower.includes("wrong tool")) return "Wrong tool";
  return description.slice(0, 35);
}

export async function getHealthData(organizationId: string): Promise<{
  agentId: string;
  evalTrend: HealthEvalPoint[];
  categoryTrend: CategoryWeekPoint[];
  activeAlarms: Alarm[];
  totalWeeks: number;
}> {
  const data = await getData(organizationId);
  const evalResultsByRunId = new Map<string, EvalResult[]>();
  for (const er of data.eval_results) {
    if (er.optimization_run_id) {
      const list = evalResultsByRunId.get(er.optimization_run_id) ?? [];
      list.push(er);
      evalResultsByRunId.set(er.optimization_run_id, list);
    }
  }

  const sortedRuns = data.runs
    .slice()
    .sort((a, b) => a.created_at.localeCompare(b.created_at));

  const evalTrend: HealthEvalPoint[] = [];
  const categoryTrend: CategoryWeekPoint[] = [];

  for (const run of sortedRuns) {
    const date = run.created_at.slice(0, 10);
    const events = eventsForRun(data.events, run.id);
    const gate = summarizeGate(run, events);
    const runEvals = evalResultsByRunId.get(run.id) ?? [];

    // Eval trend: use the best candidate score if PRs shipped, otherwise the baseline eval.
    const shippedEvals = runEvals.filter((er) => er.passed);
    const baselineEval = runEvals.find((er) => !er.passed && er.proposed_change_id == null);
    const hasData = shippedEvals.length > 0 || baselineEval != null;

    evalTrend.push({
      date,
      baseline_score: hasData
        ? average(runEvals.map((er) => er.baseline_score))
        : null,
      candidate_score: shippedEvals.length > 0
        ? average(shippedEvals.map((er) => er.candidate_score))
        : baselineEval != null
          ? baselineEval.baseline_score
          : null,
      judge_agreement_rate: hasData
        ? average(runEvals.map((er) => er.judge_agreement_rate))
        : null,
      prs_shipped: gate.prs_opened,
      run_status: run.status,
    });

    // Category trend: sum cluster sizes per semantic category.
    const categorySizes = new Map<string, number>();
    for (const clusterId of run.cluster_ids) {
      const cluster = data.clusters.find((c) => c.id === clusterId);
      if (!cluster) continue;
      const cat = _normalizeCategory(cluster.description);
      categorySizes.set(cat, (categorySizes.get(cat) ?? 0) + cluster.size);
    }
    for (const [category, size] of categorySizes) {
      categoryTrend.push({ date, category, size });
    }
  }

  const agentIds = [...new Set(sortedRuns.map((r) => r.agent_id))];

  return {
    agentId: agentIds[0] ?? "unknown",
    evalTrend,
    categoryTrend,
    activeAlarms: data.alarms ?? [],
    totalWeeks: sortedRuns.length,
  };
}
