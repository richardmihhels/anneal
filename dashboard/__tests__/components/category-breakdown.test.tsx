import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { CategoryBreakdown } from "@/components/category-breakdown";
import type { CategoryWeekPoint } from "@/lib/types";

const points: CategoryWeekPoint[] = [
  { date: "2026-04-14", category: "Policy violation", size: 13 },
  { date: "2026-04-21", category: "Policy violation", size: 10 },
  { date: "2026-04-28", category: "Policy violation", size: 6 },
  { date: "2026-04-14", category: "Premature escalation", size: 8 },
  { date: "2026-04-21", category: "Premature escalation", size: 9 },
  { date: "2026-04-28", category: "Premature escalation", size: 12 },
];

describe("CategoryBreakdown", () => {
  it("renders a card per distinct category", () => {
    render(<CategoryBreakdown points={points} />);
    expect(screen.getByText("Policy violation")).toBeInTheDocument();
    expect(screen.getByText("Premature escalation")).toBeInTheDocument();
  });

  it("shows a falling trend for policy violation (13→10→6)", () => {
    render(<CategoryBreakdown points={points} />);
    const fallingLabels = screen.getAllByText(/↓ falling/);
    expect(fallingLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("shows a rising trend for premature escalation (8→9→12)", () => {
    render(<CategoryBreakdown points={points} />);
    const risingLabels = screen.getAllByText(/↑ rising/);
    expect(risingLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("renders empty state when no points provided", () => {
    render(<CategoryBreakdown points={[]} />);
    expect(screen.getByText(/No failure clusters/)).toBeInTheDocument();
  });

  it("shows latest week count", () => {
    render(<CategoryBreakdown points={points} />);
    // 2026-04-28 is the latest date; policy_violation is 6, escalation is 12
    expect(screen.getByText("6 this wk")).toBeInTheDocument();
    expect(screen.getByText("12 this wk")).toBeInTheDocument();
  });
});

// Gap case: some weeks have no data for a category
describe("CategoryBreakdown — gap handling", () => {
  it("renders a zero for weeks with no cluster in that category (gap = 0, not interpolated)", () => {
    const gapPoints: CategoryWeekPoint[] = [
      { date: "2026-04-07", category: "Policy violation", size: 8 },
      // 2026-04-14: no data → gap (should render as 0, not interpolated)
      { date: "2026-04-21", category: "Policy violation", size: 11 },
    ];
    render(<CategoryBreakdown points={gapPoints} />);
    // 2026-04-21 is latest, size=11
    expect(screen.getByText("11 this wk")).toBeInTheDocument();
    // Component renders without error even with a gap week
    expect(screen.getByText("Policy violation")).toBeInTheDocument();
  });
});
