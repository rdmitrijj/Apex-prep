import { expect, test } from "@playwright/test";

test("register, see countdown, sign out, sign back in", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = "a-long-enough-password";

  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByLabel("Test date").fill(new Date(Date.now() + 60 * 86_400_000).toISOString().slice(0, 10));
  await page.getByLabel("Target total score").fill("1400");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByText(/days left/)).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();

  // Goals are per account and editable.
  await page.getByRole("link", { name: "Goals", exact: true }).click();
  await expect(page.getByLabel("Target total score")).toHaveValue("1400");
  await page.getByLabel("Math minimum").fill("720");
  await page.getByRole("button", { name: "Save goals" }).click();
  await expect(page.getByText("— / 720")).toBeVisible();

  await page.reload(); // session survives reload (httpOnly cookie)
  await expect(page.getByText(email)).toBeVisible();

  await page.getByRole("button", { name: "Settings" }).click();
  await expect(page.getByText("version 1.0")).toBeVisible();
  await expect(page.getByRole("link", { name: /Official SAT website/ })).toHaveAttribute("target", "_blank");
  await page.getByRole("switch", { name: "Dark theme" }).click();
  await expect(page.locator(".dark")).toHaveCount(1);
  await page.reload(); // the theme choice is remembered
  await expect(page.locator(".dark")).toHaveCount(1);
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toHaveText("Wrong email or password");

  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/days left/)).toBeVisible();
});
