import { expect, test, type Page } from "@playwright/test";

async function register(page: Page, tag: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: "No account yet? Register" }).click();
  await page.getByLabel("Email").fill(`${tag}-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("a-long-enough-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("days left")).toBeVisible();
}

async function answerCurrent(page: Page) {
  const spr = page.getByLabel("Your answer");
  await expect(spr.or(page.getByRole("radio").first())).toBeVisible(); // wait for the question to render
  if (await spr.isVisible()) await spr.fill("1");
  else await page.getByRole("radio").first().click();
}

async function submitViaReview(page: Page, label: string) {
  await page.getByRole("button", { name: /^Question \d+ of \d+/ }).click();
  await page.getByRole("button", { name: "Go to review page" }).click();
  await expect(page.getByRole("heading", { name: "Check your work" })).toBeVisible();
  await page.getByRole("button", { name: label }).click();
}

test("math exam: tools, resume after refresh, adaptive module 2, results, weakness training", async ({ page }) => {
  test.setTimeout(120_000);
  await register(page, "exam");
  await page.getByRole("link", { name: "Practice Exam" }).first().click();
  await page.getByRole("radio", { name: /^Math only/ }).check();
  await page.getByRole("radio", { name: /^Hard/ }).check();
  await page.getByRole("button", { name: "Start exam" }).click();

  await expect(page.getByRole("heading", { name: "Math: Module 1" })).toBeVisible();
  await page.getByRole("button", { name: "Start module 1" }).click();
  await expect(page.getByRole("timer")).toHaveText(/^3[45]:\d\d$/);
  await expect(page.getByText("Question 1 of 22")).toBeVisible();

  // Answer Q1, mark it for review, move on, and answer Q2.
  await answerCurrent(page);
  await page.getByRole("button", { name: "⚐ Mark for review" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("Question 2 of 22")).toBeVisible();
  await answerCurrent(page);
  await expect(page.getByText("All answers saved")).toBeVisible();

  // Refresh mid-module: the module resumes with answers, flag, and the server's clock.
  await page.reload();
  await expect(page.getByText("Question 1 of 22")).toBeVisible();
  await expect(page.getByRole("button", { name: "⚑ Marked for review" })).toBeVisible();
  await expect(page.getByRole("timer")).toHaveText(/^3[45]:\d\d$/);
  await page.getByRole("button", { name: /^Question 1 of 22/ }).click();
  await expect(page.getByRole("button", { name: "Question 1, answered, marked for review" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Question 2, answered" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Question 3, unanswered" })).toBeVisible();
  await page.getByRole("button", { name: /^Question 1 of 22/ }).click();

  // Timer hide/show, calculator, reference sheet.
  await page.getByRole("button", { name: "Hide" }).click();
  await expect(page.getByRole("timer")).toBeHidden();
  await page.getByRole("button", { name: "Show" }).click();
  await page.getByRole("button", { name: "Calculator" }).click();
  await page.getByLabel("Expression 1").fill("3*(4-1)^2");
  await expect(page.getByText("= 27")).toBeVisible();
  await page.getByLabel("Close calculator").click();
  await page.getByRole("button", { name: "Reference" }).click();
  await expect(page.getByText("Pythagorean theorem")).toBeVisible();
  await page.getByLabel("Close reference sheet").click();

  await submitViaReview(page, "Submit module");
  await expect(page.getByRole("heading", { name: "Math: Module 2" })).toBeVisible();
  await page.getByRole("button", { name: "Start module 2" }).click();
  await answerCurrent(page);
  await submitViaReview(page, "Submit and finish");

  await expect(page.getByRole("heading", { name: "Exam results" })).toBeVisible();
  await expect(page.getByText(/below your 700 target|At or above your 700 target/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Math", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Incorrect", exact: true }).click();
  await page.getByRole("button", { name: /Omitted/ }).first().click();
  await expect(page.getByText(/Math · Module \d.*Question \d+/).first()).toBeVisible();
  await page.screenshot({ path: "test-results/exam-results.png", fullPage: true });
  await expect(page.getByText("by a default curve.")).toBeVisible();

  // Log an official practice score: the exam is re-fitted to it.
  const resultsUrl = page.url();
  await page.goto("/exam");
  await page.getByLabel("R&W").fill("620");
  await page.getByLabel("Math", { exact: true }).fill("650");
  await page.getByRole("button", { name: "Add score" }).click();
  await expect(page.getByText("calibrated from 1 official score")).toBeVisible();
  await expect(page.getByText("Calibrating Math")).toBeVisible();
  await page.goto(resultsUrl);
  await expect(page.getByText(/calibrated to your official scores \(Math: 1\)/)).toBeVisible();

  await page.getByRole("link", { name: "Train my weak spots" }).click();
  await expect(page.getByRole("heading", { name: "Weakness Training" })).toBeVisible();
  await expect(page.getByText(/Missed \d+ of the last \d+/).first()).toBeVisible();
  await page.getByLabel("Questions").selectOption("10");
  await page.getByRole("button", { name: "Start training" }).click();
  await expect(page.getByText("Question 1 of 10")).toBeVisible();
  await answerCurrent(page);
  await page.getByRole("button", { name: "Check answer" }).click();
  await expect(page.getByText(/^(Correct|Not quite)(: answer .*)?$/)).toBeVisible();
});

test("full exam: R&W split pane, eliminator, break before Math", async ({ page }) => {
  test.setTimeout(120_000);
  await register(page, "full");
  await page.goto("/exam");
  await page.getByRole("button", { name: "Start exam" }).click();
  await page.getByRole("button", { name: "Start module 1" }).click();
  await expect(page.getByText("Section 1, Module 1: Reading and Writing")).toBeVisible();
  await expect(page.getByText("Question 1 of 27")).toBeVisible();

  await page.getByRole("button", { name: "Option eliminator" }).or(page.getByTitle("Option eliminator")).click();
  await page.getByRole("button", { name: "Eliminate A" }).click();
  await expect(page.getByRole("button", { name: "Undo eliminate A" })).toBeVisible();
  await page.getByRole("button", { name: "Undo eliminate A" }).click();
  await page.keyboard.press("b"); // keyboard shortcut picks B
  await expect(page.getByRole("radio", { name: /^B/ })).toHaveAttribute("aria-checked", "true");

  await submitViaReview(page, "Submit module");
  await page.getByRole("button", { name: "Start module 2" }).click();
  await submitViaReview(page, "Submit module");
  await expect(page.getByText("Break")).toBeVisible();
  await expect(page.getByRole("timer")).toHaveText(/^(10:00|9:\d\d)$/);
  await page.getByRole("button", { name: "Resume testing" }).click();
  await expect(page.getByText("Section 2, Module 1: Math")).toBeVisible();
  await page.screenshot({ path: "test-results/exam-math.png" });
});
