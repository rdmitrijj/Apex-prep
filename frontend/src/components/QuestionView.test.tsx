import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Question } from "../api/drill";
import { validSpr } from "../api/drill";
import { QuestionView } from "./QuestionView";

const mc: Question = {
  id: 1, skill_id: "MATH.ALG.LIN1.SOLVE", skill_name: "Solve", difficulty: "easy", format: "mc",
  stem: "Solve $2x = 4$.", choices: ["$1$", "$2$", "$3$", "$4$"],
};

test("MC: pick a choice, submit, then see key, rationales, and steps", async () => {
  const onSubmit = vi.fn();
  const { rerender } = render(<QuestionView q={mc} feedback={null} busy={false} error={null} onSubmit={onSubmit} />);
  const check = screen.getByRole("button", { name: "Check answer" });
  expect(check).toBeDisabled();
  await userEvent.click(screen.getAllByRole("radio")[2]);
  await userEvent.click(check);
  expect(onSubmit).toHaveBeenCalledWith("C");

  rerender(
    <QuestionView q={mc} busy={false} error={null} onSubmit={onSubmit}
      feedback={{ correct: false, answer: "B", explanation: ["Divide by 2."], rationales: { A: "Too small.", B: "Correct.", C: "Added.", D: "Doubled." } }} />,
  );
  expect(screen.getByText("Not quite")).toBeInTheDocument();
  expect(screen.getByText("Added.")).toBeInTheDocument();
  expect(screen.getByText("Divide by 2.")).toBeInTheDocument();
  expect(screen.getAllByRole("radio")[0]).toBeDisabled();
});

test("SPR: only well-formed entries can be submitted", async () => {
  const onSubmit = vi.fn();
  render(<QuestionView q={{ ...mc, format: "spr", choices: null }} feedback={null} busy={false} error={null} onSubmit={onSubmit} />);
  const input = screen.getByLabelText("Your answer");
  await userEvent.type(input, "3 1/2");
  expect(input).toHaveValue("31/2"); // space stripped
  await userEvent.clear(input);
  await userEvent.type(input, "7/2{Enter}");
  expect(onSubmit).toHaveBeenCalledWith("7/2");
});

test("validSpr mirrors the official entry rules", () => {
  for (const ok of ["7/2", "-1/3", ".6667", "0.667", "-.3333", "12345"]) expect(validSpr(ok)).toBe(true);
  for (const bad of ["3 1/2", "123456", "1,000", "$5", "-1234567", "1/2/3", ""]) expect(validSpr(bad)).toBe(false);
});

test("R&W items render the passage pane with Text 1/Text 2 and notes", () => {
  render(
    <QuestionView
      q={{ ...mc, skill_id: "RW.CAS.CTC.RESPONSE", stem: "How would the author of Text 2 respond?", passage: "First text.", passage2: "Second text.", notes: ["Note one"] }}
      feedback={null} busy={false} error={null} onSubmit={() => {}}
    />,
  );
  expect(screen.getByText("Text 1")).toBeInTheDocument();
  expect(screen.getByText("Second text.")).toBeInTheDocument();
  expect(screen.getByText("Note one")).toBeInTheDocument();
});
