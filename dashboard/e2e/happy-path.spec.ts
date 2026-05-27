import { expect, test } from "@playwright/test";

test("dashboard happy path", async ({ page }) => {
  await page.goto("/login");
  // After login the app redirects to /app (Health view — marketing page lives at /)
  await page.getByRole("button", { name: "Continue to Prompt 7 Demo" }).click();

  // Health view is now the default landing page
  await expect(
    page.getByRole("heading", { name: "Agent Health" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "Eval score trend" }),
  ).toBeVisible();
  await expect(page.getByText("Failure categories")).toBeVisible();

  // Alarm should be visible (seed data has one alarm)
  await expect(page.getByRole("alert", { name: "Active regression alarms" })).toBeVisible();
  await expect(page.getByText(/policy_violation spike detected/)).toBeVisible();

  // Navigate to Overview (demoted from default)
  await page.locator("nav").getByRole("link", { name: "Overview" }).click();
  await expect(
    page.getByRole("heading", { name: "Overview" }),
  ).toBeVisible();
  await expect(page.getByText("Regressions prevented")).toBeVisible();

  await page.locator("nav").getByRole("link", { name: "Runs" }).click();
  await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();

  const firstRun = page.locator("details").first();
  await firstRun.locator("summary").click();
  await expect(firstRun.getByText("Clusters", { exact: true })).toBeVisible();
  await expect(firstRun.getByText("Candidates", { exact: true })).toBeVisible();

  await firstRun.getByRole("link", { name: "Open run detail" }).click();
  await expect(page).toHaveURL(/\/runs\//);
  await expect(page.getByText("Pipeline timeline")).toBeVisible();
  await expect(page.getByText("Candidates tried")).toBeVisible();
  await expect(page.getByText(/Why shipped/).first()).toBeVisible();
  await page.getByRole("link", { name: "Weekly digest" }).click();
  await expect(page).toHaveURL(/\/digests\//);
  await expect(page.getByRole("heading", { name: "Weekly digest" })).toBeVisible();
  await expect(page.getByText("Shareable digest")).toBeVisible();

  await page.locator("nav").getByRole("link", { name: "Runs" }).click();
  const silentRun = page
    .locator("details")
    .filter({ has: page.locator("summary").filter({ hasText: "held" }) })
    .first();
  await silentRun.locator("summary").click();
  await silentRun.getByRole("link", { name: "Open run detail" }).click();
  await expect(page.getByText("Nothing shipped this week")).toBeVisible();
  await expect(page.getByText(/right call/)).toBeVisible();

  await page.locator("nav").getByRole("link", { name: "Connect" }).click();
  await expect(page.getByRole("heading", { name: "Connect" })).toBeVisible();
  await expect(page.getByText("Install the Anneal SDK")).toBeVisible();
  await expect(page.getByText("Install the GitHub App")).toBeVisible();
});
