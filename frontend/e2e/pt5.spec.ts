import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function scan(page: Page, name: string) {
  const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const bad = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${name}: ${v.id} (${v.nodes.length}) ${v.nodes[0]?.target.join(" ")} - ${v.help}`)).toEqual([]);
}

test("PT5 drill sets and Mini Mock", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/login");
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(`pt5-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("a-long-enough-password");
  await page.getByLabel("Test date").fill(new Date(Date.now() + 60 * 86_400_000).toISOString().slice(0, 10));
  await page.getByLabel("Target total score").fill("1300");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Mastery by skill" })).toBeVisible();

  await page.getByRole("link", { name: "PT5 Drill" }).click();
  await expect(page.getByRole("heading", { name: "PT5 Weakness Drill" })).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Overall readiness" })).toBeVisible();
  await scan(page, "pt5 overview");

  await page.goto("/pt5?set=rw-trans");
  await expect(page.getByRole("heading", { name: "Transitions" })).toBeVisible();
  await scan(page, "rule card");
  await page.getByRole("button", { name: "Start the 30 questions" }).click();
  await expect(page.getByText("Question 1 of 30")).toBeVisible();
  // Answer every choice in turn until one is wrong (the first wrong pick shows the trap).
  await page.getByRole("radio").first().check();
  await page.getByRole("button", { name: "Check answer" }).click();
  await expect(page.getByRole("button", { name: "Next question" })).toBeVisible();
  await scan(page, "drill feedback");

  await page.goto("/pt5?cards=1");
  await expect(page.getByRole("heading", { name: "Warm-up: rule cards" })).toBeVisible();

  await page.goto("/triage?mock=rw&form=A");
  await expect(page.getByText("Question 1 of 27")).toBeVisible();
  await scan(page, "mini mock");
  await page.getByRole("button", { name: /^Finish/ }).click();
  await expect(page.getByRole("heading", { name: "Mini Mock R&W, form A results" })).toBeVisible();
  await expect(page.getByText("27", { exact: true })).toBeVisible(); // 27 blanks
  await scan(page, "mini mock results");
});
