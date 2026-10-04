import { render, screen } from "@testing-library/react";
import { ScoreTrend } from "./ScoreTrend";

test("same-day results share one date label and end labels never overprint", () => {
  const { container } = render(
    <ScoreTrend
      points={[
        { date: "2026-10-04T09:00:00", rw: 470, math: 460, official: false },
        { date: "2026-10-04T15:00:00", rw: 560, math: 590, official: true },
      ]}
    />,
  );
  expect(screen.getAllByText(/^Oct 4|^4 Oct/)).toHaveLength(1);
  const rw = screen.getByText("R&W 470");
  const math = screen.getByText("Math 460");
  expect(Math.abs(Number(rw.getAttribute("y")) - Number(math.getAttribute("y")))).toBeGreaterThanOrEqual(13);
  expect(container.querySelectorAll("svg[role=img] circle[fill='white']")).toHaveLength(2); // official = hollow rings
});
