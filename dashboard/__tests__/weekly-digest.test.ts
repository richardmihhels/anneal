import { getWeeklyDigest, getWeeklyDigestForRun, listRunDetails } from "@/lib/data";

describe("weekly digest data", () => {
  it("renders the same body for email and dashboard page", async () => {
    const run = (await listRunDetails("org_demo")).find(
      (candidate) => candidate.gate.prs_opened > 0,
    );
    expect(run).toBeDefined();
    expect(run!.gate.prs_opened).toBe(1);
    expect(run!.proposed_changes.filter((change) => change.published)).toHaveLength(1);
    expect(run!.proposed_changes.length).toBeGreaterThan(1);

    const digest = await getWeeklyDigestForRun(run!.id, "org_demo");
    expect(digest).not.toBeNull();
    expect(digest!.email_body).toBe(digest!.page_body);
    expect(digest!.email_body).toContain("PRs");
    expect(digest!.summary).toContain("Anneal shipped 1 PR this week");

    const byId = await getWeeklyDigest(digest!.id, "org_demo");
    expect(byId).toEqual(digest);
  });

  it("keeps silent weeks explicit and non-apologetic", async () => {
    const run = (await listRunDetails("org_demo")).find(
      (candidate) => candidate.gate.rejected > 0 && candidate.gate.prs_opened === 0,
    );
    expect(run).toBeDefined();

    const digest = await getWeeklyDigestForRun(run!.id, "org_demo");
    expect(digest).not.toBeNull();
    expect(digest!.email_body).toContain("No PR shipped this week");
    expect(digest!.email_body).toContain("safe outcome");
    expect(digest!.email_body.toLowerCase()).not.toContain("sorry");
  });
});
