import { expect, test } from "@playwright/test";

test("R&W drill: passage pane, notes/figures, feedback, report a problem", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(`rw-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("a-long-enough-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("link", { name: "Topic Drill" }).first().click();

  await page.getByRole("checkbox", { name: "Command of Evidence: Quantitative", exact: true }).check();
  await page.getByLabel("Questions").selectOption("5");
  await page.getByRole("button", { name: "Start drill" }).click();

  await expect(page.getByRole("button", { name: "Check answer" })).toBeVisible();
  await expect(page.getByText(/most effectively uses data from the (table|graph)/)).toBeVisible();
  await expect(page.locator("table, svg[role=img]").first()).toBeVisible();
  await page.screenshot({ path: "test-results/rw-question.png", fullPage: true });
  await page.getByRole("radio").first().click();
  await page.getByRole("button", { name: "Check answer" }).click();
  await expect(page.getByText(/^(Correct|Not quite)$/)).toBeVisible();
  await expect(page.getByText(/^Correct\./)).toBeVisible(); // the key's rationale is shown

  await page.getByRole("button", { name: "Report a problem" }).click();
  await page.getByLabel("What's wrong?").fill("Testing the report flow");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/hidden until it's reviewed/)).toBeVisible();
  await page.getByRole("button", { name: "Next question" }).click();
  await expect(page.getByText("Question 2 of 5")).toBeVisible();
  await expect(page.getByRole("button", { name: "Check answer" })).toBeVisible();
});
