import { expect, test } from "@playwright/test";

test("marketing homepage renders", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText(/measurably better/i)).toBeVisible();
  await expect(page.getByText(/never worse/i)).toBeVisible();

  await expect(page.getByRole("figure", { name: /example anneal pull request/i })).toBeVisible();
  await expect(page.getByText(/\+6\.2%/)).toBeVisible();
});

test("marketing nav Request access link points to waitlist", async ({ page }) => {
  await page.goto("/");
  const navCta = page.locator("header a", { hasText: "Request access" });
  await expect(navCta).toBeVisible();
  await expect(navCta).toHaveAttribute("href", "#waitlist");
});

test("email capture — valid email shows success", async ({ page }) => {
  await page.goto("/");

  const input = page.getByRole("textbox", { name: /work email/i });
  await input.fill("test@example.com");
  await page.getByRole("button", { name: /request access/i }).click();

  await expect(page.getByText(/on the list/i)).toBeVisible();
  await expect(input).not.toBeVisible();
});

test("email capture — invalid email shows error", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("textbox", { name: /work email/i }).fill("notvalid");
  await page.getByRole("button", { name: /request access/i }).click();

  await expect(page.getByRole("alert")).toBeVisible();
});

test("email capture — keyboard accessible", async ({ page }) => {
  await page.goto("/");

  const input = page.getByRole("textbox", { name: /work email/i });
  await input.focus();
  await input.fill("kb@example.com");
  await input.press("Tab");
  await page.keyboard.press("Enter");

  await expect(page.getByText(/on the list/i)).toBeVisible();
});
