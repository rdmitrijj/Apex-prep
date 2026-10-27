import { renderToStaticMarkup } from "react-dom/server";
import { MathText, renderMath } from "./MathText";

// Every text a seed question can show must render without KaTeX errors or leftover TeX.
type Item = Record<string, unknown>;
const FILES = import.meta.glob<Item[]>("../../../backend/app/seed/{rw,math}/*.json", { eager: true, import: "default" });
const texts = (it: Item): string[] =>
  [it.passage, it.passage2, it.stem, it.explanation, it.choices, it.notes, Object.values((it.rationales as object) ?? {})]
    .flat()
    .filter((t): t is string => typeof t === "string");

test("seed files are found", () => expect(Object.keys(FILES).length).toBeGreaterThan(10));

test("every seed question renders cleanly", () => {
  const bad: string[] = [];
  for (const items of Object.values(FILES))
    for (const it of items)
      for (const t of texts(it)) {
        const broken = renderToStaticMarkup(<MathText text={t} />).includes("katex-error");
        // Text outside math: an escaped \$ comes back as exactly "$"; any other $ or TeX command leaked.
        const leaked = renderMath(t).some((n) => typeof n === "string" && n !== "$" && /\$|\\[a-zA-Z]+/.test(n));
        if (broken || leaked) bad.push(`${String(it.id)}: ${t.slice(0, 60)}`);
      }
  expect(bad).toEqual([]);
});
