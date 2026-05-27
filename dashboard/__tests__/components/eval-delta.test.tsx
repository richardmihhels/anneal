import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { EvalDelta, RejectedDelta } from "@/components/eval-delta";
import type { EvalResult } from "@/lib/types";

const mockEval: EvalResult = {
  id: "eval-1",
  proposed_change_id: "change-1",
  run_at: "2026-05-26T10:00:00Z",
  baseline_score: 0.0,
  candidate_score: 1.0,
  delta: 1.0,
  p_value: 0.001,
  sample_size: 24,
  passed: true,
  judge_agreement_rate: 1.0,
};

describe("EvalDelta", () => {
  it("shows delta as percentage", () => {
    render(<EvalDelta eval_result={mockEval} />);
    expect(screen.getByText("+100%")).toBeInTheDocument();
  });

  it("shows before and after scores", () => {
    render(<EvalDelta eval_result={mockEval} />);
    expect(screen.getByText("0% → 100%")).toBeInTheDocument();
  });

  it("shows p-value", () => {
    render(<EvalDelta eval_result={mockEval} />);
    expect(screen.getByText("p=0.001, n=24")).toBeInTheDocument();
  });

  it("shows p<0.001 for very small p-values", () => {
    render(<EvalDelta eval_result={{ ...mockEval, p_value: 0.0 }} />);
    expect(screen.getByText("p<0.001, n=24")).toBeInTheDocument();
  });

  it("compact mode shows only delta and p", () => {
    const { container } = render(<EvalDelta eval_result={mockEval} compact />);
    expect(container.textContent).toContain("+100%");
  });

  it("judge agreement rate shown", () => {
    render(<EvalDelta eval_result={mockEval} />);
    expect(screen.getByText(/judge agreement 100%/)).toBeInTheDocument();
  });
});

describe("RejectedDelta", () => {
  it("shows default rejection message", () => {
    render(<RejectedDelta />);
    expect(screen.getByText(/did not beat baseline/)).toBeInTheDocument();
  });

  it("shows custom reason", () => {
    render(<RejectedDelta reason="p=0.18 ≥ 0.05" />);
    expect(screen.getByText(/p=0.18/)).toBeInTheDocument();
  });
});
