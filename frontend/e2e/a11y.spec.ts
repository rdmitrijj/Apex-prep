import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function scan(page: Page, name: string) {
  const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const bad = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${name}: ${v.id} (${v.nodes.length}) ${v.nodes[0]?.target.join(" ")} - ${v.help}`)).toEqual([]);
}

test("main pages have no serious accessibility violations", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/login");
  await scan(page, "login");
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(`a11y-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("a-long-enough-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Mastery by skill" })).toBeVisible();
  await scan(page, "home");
  for (const [path, heading] of [
    ["/plan", "This week's plan"],
    ["/drill", "Topic Drill"],
    ["/training", "Weakness Training"],
    ["/mistakes", "Mistake Notebook"],
    ["/exam", "Practice Exam"],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await scan(page, path);
  }
  await page.getByRole("button", { name: "Start exam" }).click();
  await page.getByRole("button", { name: "Start module 1" }).click();
  await expect(page.getByText("Question 1 of 27")).toBeVisible();
  await scan(page, "exam runner");
  await page.getByRole("button", { name: /^Question 1 of 27/ }).click();
  await scan(page, "exam navigator");

  // A short Math-only exam to scan the results page (with an expanded question).
  await page.goto("/exam");
  page.once("dialog", (d) => d.accept()); // replaces the exam in progress
  await page.getByRole("radio", { name: /^Math only/ }).check();
  await page.getByRole("button", { name: "Start exam" }).click();
  for (const label of ["Submit module", "Submit and finish"]) {
    await page.getByRole("button", { name: /^Start module/ }).click();
    await page.getByRole("button", { name: /^Question 1 of/ }).click();
    await page.getByRole("button", { name: "Go to review page" }).click();
    await page.getByRole("button", { name: label }).click();
  }
  await expect(page.getByRole("heading", { name: "Exam results" })).toBeVisible();
  await page.getByRole("button", { name: /Omitted/ }).first().click();
  await scan(page, "results");
});
