import { expect, test } from "@playwright/test";

test("mistake notebook: tag a miss, filter, retry similar", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(`notebook-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("a-long-enough-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("days left")).toBeVisible();

  await page.goto("/drill");
  await page.getByRole("checkbox", { name: "Linear equations in one variable", exact: true }).check({ force: true });
  await page.getByLabel("Questions").selectOption("30");
  await page.getByRole("button", { name: "Start drill" }).click();
  // Answer until one is wrong (always the first choice, or "1"), then tag why.
  for (let i = 0; i < 30; i++) {
    const spr = page.getByLabel("Your answer");
    await expect(page.getByRole("button", { name: "Check answer" })).toBeVisible();
    if (await spr.isVisible()) await spr.fill("1");
    else await page.getByRole("radio").first().click();
    await page.getByRole("button", { name: "Check answer" }).click();
    const verdict = page.getByText(/^(Correct|Not quite)(: answer .*)?$/);
    await expect(verdict).toBeVisible();
    if ((await verdict.textContent())!.startsWith("Not quite")) break;
    await page.getByRole("button", { name: "Next question" }).click();
  }
  await page.getByRole("button", { name: "Careless slip" }).click();
  await expect(page.getByRole("button", { name: "Careless slip" })).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("link", { name: "Mistakes" }).click();
  await expect(page.getByRole("heading", { name: "Mistake Notebook" })).toBeVisible();
  await page.getByLabel("Reason").selectOption("careless");
  const row = page.getByRole("button", { name: /Drill .*Careless slip/ });
  await expect(row).toHaveCount(1);
  await page.getByLabel("Reason").selectOption("untagged");
  await expect(page.getByText("No mistakes here. Nice.")).toBeVisible();
  await page.getByLabel("Reason").selectOption("");
  await page.getByRole("button", { name: /Drill .*Careless slip/ }).click();
  await expect(page.getByText(/^(You answered .*|Left blank) · \d+ s$/)).toBeVisible();
  await page.getByRole("link", { name: "Retry 3 similar questions" }).click();
  await expect(page.getByText("Question 1 of 3")).toBeVisible();
});
