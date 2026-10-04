import { expect, test } from "@playwright/test";

test("first visit: diagnostic offer, today's plan, week view, heatmap", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(`plan-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("a-long-enough-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Start with a diagnostic" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Diagnostic: full practice exam" })).toBeVisible();
  await expect(page.getByRole("button", { name: /: not tried yet$/ })).toHaveCount(91); // one heatmap cell per sub-skill
  await page.screenshot({ path: "test-results/home-fresh.png", fullPage: true });

  await page.getByRole("link", { name: "Whole week →" }).click();
  await expect(page.getByRole("heading", { name: "This week's plan" })).toBeVisible();
  await expect(page.getByText("· today")).toBeVisible();
  await page.getByRole("button", { name: "Rebuild from my latest weaknesses" }).click();
  await expect(page.getByRole("button", { name: "Rebuild from my latest weaknesses" })).toBeEnabled();
  await page.screenshot({ path: "test-results/plan.png", fullPage: true });

  await page.goto("/");
  await page.getByRole("link", { name: "Log an official score" }).click();
  await expect(page.getByRole("heading", { name: "Official scores and calibration" })).toBeInViewport();
});
