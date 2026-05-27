import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { EvalScoreTrend } from "@/components/eval-score-trend";
import type { EvalScorePoint } from "@/lib/types";

const points: EvalScorePoint[] = [
  {
    date: "2026-05-05",
    baseline_score: 0.4,
    candidate_score: 0.65,
    delta: 0.25,
    prs: 1,
    rejected: 0,
  },
  {
    date: "2026-05-12",
    baseline_score: null,
    candidate_score: null,
    delta: null,
    prs: 0,
    rejected: 3,
  },
];

describe("EvalScoreTrend", () => {
  it("renders an accessible eval score chart", () => {
    render(<EvalScoreTrend points={points} />);
    expect(
      screen.getByRole("img", { name: "Eval score trend" }),
    ).toBeInTheDocument();
  });

  it("shows quiet held weeks without pretending there was an eval", () => {
    render(<EvalScoreTrend points={points} />);
    expect(screen.getByText("3 held")).toBeInTheDocument();
    expect(screen.getAllByText("no eval").length).toBeGreaterThan(0);
  });
});
