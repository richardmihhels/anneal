import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { Nav } from "@/components/nav";
import type { AuthSession } from "@/lib/auth";

jest.mock("next/navigation", () => ({
  usePathname: () => "/runs",
}));

const session: AuthSession = {
  userId: "user_demo_lead",
  email: "lead@prompt7.example",
  organizationId: "org_demo",
  organizationName: "Prompt 7 Demo",
  expiresAt: Date.now() + 60_000,
};

describe("Nav", () => {
  it("renders org session controls", () => {
    render(<Nav session={session} />);

    expect(screen.getByText("Prompt 7 Demo")).toBeInTheDocument();
    expect(screen.getByText("lead@prompt7.example")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign out" })).toHaveAttribute(
      "href",
      "/logout",
    );
  });

  it("renders sign-in link without a session", () => {
    render(<Nav session={null} />);

    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login",
    );
  });
});
