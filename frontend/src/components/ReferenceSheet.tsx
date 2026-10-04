import { MathText } from "./MathText";

const FORMULAS: [string, string][] = [
  ["Circle", "$A = \\pi r^2$, $\\; C = 2\\pi r$"],
  ["Rectangle", "$A = \\ell w$"],
  ["Triangle", "$A = \\tfrac{1}{2}bh$"],
  ["Pythagorean theorem", "$c^2 = a^2 + b^2$"],
  ["Special right triangles", "$30°\\text{-}60°\\text{-}90°$: $x,\\ x\\sqrt{3},\\ 2x$; $\\;45°\\text{-}45°\\text{-}90°$: $s,\\ s,\\ s\\sqrt{2}$"],
  ["Rectangular prism", "$V = \\ell w h$"],
  ["Cylinder", "$V = \\pi r^2 h$"],
  ["Sphere", "$V = \\tfrac{4}{3}\\pi r^3$"],
  ["Cone", "$V = \\tfrac{1}{3}\\pi r^2 h$"],
  ["Pyramid", "$V = \\tfrac{1}{3}\\ell w h$"],
];

export function ReferenceSheet({ onClose }: { onClose: () => void }) {
  return (
    <aside aria-label="Reference sheet" className="fixed right-4 top-20 z-30 w-[380px] max-w-[calc(100vw-2rem)] rounded-lg border border-slate-300 bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-100 px-3 py-1.5">
        <span className="text-sm font-semibold">Reference</span>
        <button type="button" onClick={onClose} aria-label="Close reference sheet" className="px-1 text-lg leading-none">×</button>
      </div>
      <dl className="space-y-2 p-4 text-sm">
        {FORMULAS.map(([name, f]) => (
          <div key={name} className="flex justify-between gap-4">
            <dt className="text-slate-600">{name}</dt>
            <dd className="text-right"><MathText text={f} /></dd>
          </div>
        ))}
        <p className="border-t border-slate-200 pt-2 text-slate-600">
          A circle has <MathText text="$360°$" /> (<MathText text="$2\pi$" /> radians). The angles of a triangle sum to <MathText text="$180°$" />.
        </p>
      </dl>
    </aside>
  );
}
