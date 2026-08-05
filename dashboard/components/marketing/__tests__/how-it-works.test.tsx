import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { HowItWorks } from "../how-it-works";

describe("HowItWorks", () => {
  it("renders the continuous assurance loop in order", () => {
    render(<HowItWorks />);

    const headings = screen.getAllByRole("heading", { level: 3 });
    expect(headings.map((heading) => heading.textContent)).toEqual([
      "Connect",
      "Watch",
      "Detect",
      "Improve",
    ]);
    expect(screen.getByText(/background queue/i)).toBeInTheDocument();
    expect(screen.getByText(/health view shows recorded eval scores/i)).toBeInTheDocument();
    expect(screen.getByText(/one-sided proportions test/i)).toBeInTheDocument();
    expect(screen.getByText(/digest records the safe outcome/i)).toBeInTheDocument();
  });
});
