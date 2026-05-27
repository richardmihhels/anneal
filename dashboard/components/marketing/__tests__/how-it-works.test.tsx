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
      "Alarm",
      "Improve",
    ]);
    expect(screen.getByText(/traces stream in immediately/i)).toBeInTheDocument();
    expect(screen.getByText(/health view shows eval score/i)).toBeInTheDocument();
    expect(screen.getByText(/sends a precise alarm within hours/i)).toBeInTheDocument();
    expect(screen.getByText(/digest still tells you what was seen/i)).toBeInTheDocument();
  });
});
