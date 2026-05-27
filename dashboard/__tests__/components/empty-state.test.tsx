import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/empty-state";

describe("EmptyState", () => {
  it("no-clusters — reassuring message, no error language", () => {
    render(<EmptyState kind="no-clusters" />);
    expect(screen.getByText(/Agent performing well/)).toBeInTheDocument();
    expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
  });

  it("no-survivors — explains the gate prevented noise", () => {
    render(<EmptyState kind="no-survivors" clusterCount={3} rejectedCount={3} />);
    expect(screen.getByText(/Nothing shipped this week/)).toBeInTheDocument();
    expect(screen.getByText(/p < 0.05 gate/)).toBeInTheDocument();
  });

  it("no-survivors — uses silenceReport when provided", () => {
    const msg = "Anneal evaluated 4 clusters and found nothing worth shipping.";
    render(<EmptyState kind="no-survivors" silenceReport={msg} />);
    expect(screen.getByText(msg)).toBeInTheDocument();
  });

  it("too-few-traces — explains skipped reason", () => {
    render(<EmptyState kind="too-few-traces" />);
    expect(screen.getByText(/Skipped — low traffic/)).toBeInTheDocument();
    expect(screen.getByText(/fewer than 20 traces/i)).toBeInTheDocument();
  });

  it("failed — shows error state", () => {
    render(<EmptyState kind="failed" />);
    expect(screen.getByText(/Pipeline error/)).toBeInTheDocument();
  });
});
