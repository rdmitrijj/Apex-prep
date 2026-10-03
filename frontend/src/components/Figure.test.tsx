import { render, screen } from "@testing-library/react";
import { Figure } from "./Figure";

test("renders every figure kind without crashing", () => {
  render(
    <>
      <Figure spec={{ kind: "table", header: ["$x$", "$y$"], rows: [["1", "2"]] }} />
      <Figure spec={{ kind: "bars", labels: ["0", "1"], values: [3, 5], xlabel: "Pets", ylabel: "Households" }} />
      <Figure spec={{ kind: "line", x: [2000, 2010], series: [{ name: "A", values: [1, 2] }, { name: "B", values: [2, 1] }] }} />
      <Figure spec={{ kind: "plot", x: [-5, 5], y: [-5, 5], curves: [[[-5, -5], [5, 5]]], points: [[1, 1, "(1, 1)"]] }} />
      <Figure spec={{ kind: "shape", points: { A: [0, 0], B: [4, 0], C: [0, 3] }, segments: [["A", "B"], ["B", "C"], ["C", "A"]], labels: [{ at: [2, -0.4], text: "4" }], right_angles: ["A"] }} />
    </>,
  );
  expect(screen.getByRole("img", { name: "Bar graph" })).toBeInTheDocument();
  expect(screen.getByText("Pets")).toBeInTheDocument();
  expect(screen.getByText("(1, 1)")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Geometric figure" })).toBeInTheDocument();
  expect(screen.getAllByRole("table")).toHaveLength(1);
});
