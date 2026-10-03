import { expect, test } from "@playwright/test";

test("topic drill: pick a math skill, answer, see worked solution, finish", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(`drill-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("a-long-enough-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await page.getByRole("link", { name: "Topic Drill" }).first().click();
  await expect(page.getByRole("heading", { name: "Topic Drill" })).toBeVisible();
  await page.getByRole("checkbox", { name: "Linear equations in one variable", exact: true }).check({ force: true });
  await page.getByLabel("Questions").selectOption("5");
  await page.getByRole("button", { name: "Start drill" }).click();

  for (let i = 1; i <= 5; i++) {
    await expect(page.getByText(`Question ${i} of 5`)).toBeVisible();
    await expect(page.getByRole("button", { name: "Check answer" })).toBeVisible();
    const spr = page.getByLabel("Your answer");
    if (await spr.isVisible()) await spr.fill("1");
    else await page.getByRole("radio").first().click();
    await page.getByRole("button", { name: "Check answer" }).click();
    await expect(page.getByText(/^(Correct|Not quite)(: answer .*)?$/)).toBeVisible();
    await expect(page.locator(".katex").first()).toBeVisible();
    if (i < 5) await page.getByRole("button", { name: "Next question" }).click();
  }
  await expect(page.getByText(/Done: \d of 5 correct/)).toBeVisible();
  await page.screenshot({ path: "test-results/drill-done.png", fullPage: true });
  await page.getByRole("button", { name: "Back to skills" }).click();
  // accuracy now shows for the drilled skill
  await expect(page.getByTitle(/of 5 correct/).first()).toBeVisible();
});
