import { offsetIn, rangeFor } from "./Annotations";

test("text offsets round-trip across nested nodes", () => {
  const root = document.createElement("div");
  root.innerHTML = "<p>Alpha <b>beta</b> gamma</p><p>delta</p>";
  document.body.appendChild(root);
  const beta = root.querySelector("b")!.firstChild!;
  const start = offsetIn(root, beta, 1)!; // "eta gam"
  const end = offsetIn(root, root.querySelector("p")!.lastChild!, 4)!;
  expect(rangeFor(root, start, end)!.toString()).toBe("eta gam");
  expect(rangeFor(root, 0, 5)!.toString()).toBe("Alpha");
  expect(rangeFor(root, 999, 1000)).toBeNull();
  expect(offsetIn(root, document.createTextNode("x"), 0)).toBeNull();
});
