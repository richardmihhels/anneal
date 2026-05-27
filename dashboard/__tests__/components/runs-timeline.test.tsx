import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { RunsTimeline } from "@/components/runs-timeline";
import type { RunDetail } from "@/lib/types";

const run: RunDetail = {
  id: "aaa27086-58ff-4cf1-a70f-f2ed17659b95",
  agent_id: "cascade-support-v1",
  created_at: "2026-05-26T09:46:00Z",
  status: "completed",
  cluster_ids: ["cluster-1"],
  proposed_change_ids: ["change-1"],
  events: [],
  clusters: [
    {
      id: "cluster-1",
      label: "wrong-tool",
      description: "Agent picked the wrong billing tool",
      trace_ids: ["trace-1", "trace-2"],
      size: 2,
      created_at: "2026-05-26T09:46:00Z",
      representative_trace_id: "trace-1",
    },
  ],
  proposed_changes: [
    {
      id: "change-1",
      optimization_run_id: "aaa27086-58ff-4cf1-a70f-f2ed17659b95",
      target: "system_prompt",
      before: "baseline",
      after: "candidate",
      rationale: "Target failure: wrong tool",
      eval_result_id: "eval-1",
      eval_result: {
        id: "eval-1",
        proposed_change_id: "change-1",
        run_at: "2026-05-26T09:47:00Z",
        baseline_score: 0.5,
        candidate_score: 0.8,
        delta: 0.3,
        p_value: 0.01,
        sample_size: 24,
        passed: true,
        judge_agreement_rate: 0.95,
      },
    },
  ],
  silence_report: null,
  gate: {
    survivors: 1,
    rejected: 2,
    holdout_size: 24,
    prs_opened: 1,
  },
};

describe("RunsTimeline", () => {
  it("renders expandable run summaries with cluster and candidate context", () => {
    render(<RunsTimeline runs={[run]} />);
    expect(screen.getByText("aaa27086-58f")).toBeInTheDocument();
    expect(screen.getByText("1 shipped")).toBeInTheDocument();
    expect(
      screen.getByText("Agent picked the wrong billing tool"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Shipped because the holdout eval beat baseline/),
    ).toBeInTheDocument();
  });
});
