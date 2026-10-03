import { expect, test } from "@playwright/test";

test("register, see countdown, sign out, sign back in", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = "a-long-enough-password";

  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByText(/days left/)).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();

  await page.reload(); // session survives reload (httpOnly cookie)
  await expect(page.getByText(email)).toBeVisible();

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
