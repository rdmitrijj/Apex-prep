import { render } from "@testing-library/react";
import { MathText } from "./MathText";

test("renders inline/display math, literal dollars, and underlines", () => {
  const { container } = render(<MathText text={"Costs \\$5 when $x^2 = 4$. $$y = 1$$ <u>key part</u>"} />);
  expect(container.textContent).toContain("Costs $5 when");
  expect(container.querySelectorAll(".katex").length).toBe(2);
  expect(container.querySelector(".katex-display")).not.toBeNull();
  expect(container.querySelector("u")?.textContent).toBe("key part");
});

test("plain text is escaped, not injected as HTML", () => {
  const { container } = render(<MathText text={'<img src=x onerror="alert(1)">'} />);
  expect(container.querySelector("img")).toBeNull();
});
