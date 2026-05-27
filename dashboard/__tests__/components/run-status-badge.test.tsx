import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { RunStatusBadge } from "@/components/run-status-badge";

describe("RunStatusBadge", () => {
  it("renders completed", () => {
    render(<RunStatusBadge status="completed" />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders failed with red styling", () => {
    const { container } = render(<RunStatusBadge status="failed" />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-red-400");
  });

  it("renders running with blue styling", () => {
    const { container } = render(<RunStatusBadge status="running" />);
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-blue-400");
  });

  it("renders pending with zinc styling", () => {
    const { container } = render(<RunStatusBadge status="pending" />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("text-zinc-400");
  });

  it("applies sm size class", () => {
    const { container } = render(<RunStatusBadge status="completed" size="sm" />);
    expect(container.firstChild).toHaveClass("px-1.5");
  });
});
