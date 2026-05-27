import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { HealthViewMock } from "../health-view-mock";

describe("HealthViewMock", () => {
  it("renders the Agent Health preview", () => {
    render(<HealthViewMock />);

    expect(
      screen.getByRole("figure", { name: /agent health view preview/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Agent Health")).toBeInTheDocument();
    expect(screen.getByText("91.8%")).toBeInTheDocument();
    expect(screen.getByText("Policy spike cleared")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /eval score trend rising over time/i }),
    ).toBeInTheDocument();
  });
});
