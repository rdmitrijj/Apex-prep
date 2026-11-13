import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RuleCard } from "./RuleCard";

describe("RuleCard", () => {
  it("renders the title, bold labels, and both list kinds", () => {
    const { container } = render(<RuleCard markdown={"# Transitions\n**Rule.** Name the *relationship*.\n**Method.**\n1. Cover the choices.\n2. Name it.\n**Watch for.**\n- Hence vs However"} />);
    expect(screen.getByRole("heading", { name: "Transitions" })).toBeInTheDocument();
    expect(container.querySelector("strong")?.textContent).toBe("Rule.");
    expect(container.querySelector("em")?.textContent).toBe("relationship");
    expect(container.querySelectorAll("ol li")).toHaveLength(2);
    expect(container.querySelectorAll("ul li")).toHaveLength(1);
  });
});
