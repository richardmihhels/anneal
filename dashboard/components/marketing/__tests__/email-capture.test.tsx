import { render, screen, fireEvent } from "@testing-library/react";
import { EmailCapture } from "../email-capture";

describe("EmailCapture", () => {
  it("renders the email input and submit button", () => {
    render(<EmailCapture />);
    expect(screen.getByRole("textbox", { name: /work email/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /request access/i })).toBeInTheDocument();
  });

  it("shows success message on valid email submission", () => {
    render(<EmailCapture />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "eng@example.com" },
    });
    fireEvent.submit(screen.getByRole("form", { name: /beta waitlist/i }));
    expect(screen.getByText(/on the list/i)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("shows error on empty submission", () => {
    render(<EmailCapture />);
    fireEvent.submit(screen.getByRole("form", { name: /beta waitlist/i }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/valid email/i);
  });

  it("shows error on invalid email format", () => {
    render(<EmailCapture />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "notanemail" },
    });
    fireEvent.submit(screen.getByRole("form", { name: /beta waitlist/i }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });

  it("clears error when user starts correcting input", () => {
    render(<EmailCapture />);
    fireEvent.submit(screen.getByRole("form", { name: /beta waitlist/i }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "f" },
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
