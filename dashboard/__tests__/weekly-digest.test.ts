import { getWeeklyDigest, getWeeklyDigestForRun, listRunDetails } from "@/lib/data";

describe("weekly digest data", () => {
  it("renders the same body for email and dashboard page", () => {
    const run = listRunDetails("org_demo").find((candidate) => candidate.gate.prs_opened > 0);
    expect(run).toBeDefined();

    const digest = getWeeklyDigestForRun(run!.id, "org_demo");
    expect(digest).not.toBeNull();
    expect(digest!.email_body).toBe(digest!.page_body);
    expect(digest!.email_body).toContain("PRs");

    const byId = getWeeklyDigest(digest!.id, "org_demo");
    expect(byId).toEqual(digest);
  });

  it("keeps silent weeks explicit and non-apologetic", () => {
    const run = listRunDetails("org_demo").find(
      (candidate) => candidate.gate.rejected > 0 && candidate.gate.prs_opened === 0,
    );
    expect(run).toBeDefined();

    const digest = getWeeklyDigestForRun(run!.id, "org_demo");
    expect(digest).not.toBeNull();
    expect(digest!.email_body).toContain("No PR shipped this week");
    expect(digest!.email_body).toContain("safe outcome");
    expect(digest!.email_body.toLowerCase()).not.toContain("sorry");
  });
});
