import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { AlarmBanner } from "@/components/alarm-banner";
import type { Alarm } from "@/lib/types";

const alarm: Alarm = {
  id: "alarm-1",
  organization_id: "org_demo",
  agent_id: "cascade-support-v1",
  category: "policy_violation",
  baseline_rate: 0.06,
  current_rate: 0.28,
  window_hours: 24,
  affected_trace_count: 14,
  first_detected: new Date(Date.now() - 3_600_000).toISOString(), // 1h ago
  cause_hypothesis:
    "Hypothesis (AI-generated — treat as a guess): Rate rose from 6.0% to 28.0%.",
  notified: true,
};

describe("AlarmBanner", () => {
  it("renders nothing when there are no alarms", () => {
    const { container } = render(<AlarmBanner alarms={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders alarm with category, rates, and affected count", () => {
    render(<AlarmBanner alarms={[alarm]} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/policy_violation/)).toBeInTheDocument();
    // Rate values live in <span> elements; getAllByText handles multiple matches
    expect(screen.getAllByText(/6\.0%/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/28\.0%/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/14 conversation/)).toBeInTheDocument();
  });

  it("labels the alert region accessibly", () => {
    render(<AlarmBanner alarms={[alarm]} />);
    expect(
      screen.getByRole("alert", { name: "Active regression alarms" }),
    ).toBeInTheDocument();
  });

  it("includes the cause hypothesis", () => {
    render(<AlarmBanner alarms={[alarm]} />);
    expect(screen.getByText(/treat as a guess/)).toBeInTheDocument();
  });

  it("renders multiple alarms", () => {
    const alarm2: Alarm = {
      ...alarm,
      id: "alarm-2",
      category: "wrong_tool",
      baseline_rate: 0.04,
      current_rate: 0.20,
    };
    render(<AlarmBanner alarms={[alarm, alarm2]} />);
    expect(screen.getByText(/policy_violation/)).toBeInTheDocument();
    expect(screen.getByText(/wrong_tool/)).toBeInTheDocument();
  });
});
