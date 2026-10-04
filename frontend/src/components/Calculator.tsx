import { useEffect, useMemo, useRef, useState } from "react";

type MathJs = typeof import("mathjs");
type DesmosCalc = { destroy: () => void };
declare global {
  interface Window {
    Desmos?: { GraphingCalculator: (el: HTMLElement, opts?: object) => DesmosCalc };
  }
}

const DESMOS_KEY = import.meta.env.VITE_DESMOS_API_KEY as string | undefined;

function Desmos({ apiKey }: { apiKey: string }) {
  const el = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let calc: DesmosCalc | undefined;
    const mount = () => {
      if (el.current && window.Desmos) calc = window.Desmos.GraphingCalculator(el.current, { expressionsCollapsed: false });
    };
    if (window.Desmos) mount();
    else {
      const s = document.createElement("script");
      s.src = `https://www.desmos.com/api/v1.11/calculator.js?apiKey=${encodeURIComponent(apiKey)}`;
      s.onload = mount;
      s.onerror = () => setFailed(true);
      document.head.appendChild(s);
    }
    return () => calc?.destroy();
  }, [apiKey]);
  if (failed) return <Fallback />;
  return <div ref={el} className="h-full min-h-[420px] w-full" />;
}

const W = 320;
const H = 240;

type Line = { text: string; value?: string; error?: string; fn?: (x: number) => number };

// math.js expression list: each line is evaluated in a shared scope; anything in x is plotted.
function Fallback() {
  const [math, setMath] = useState<MathJs | null>(null);
  const [texts, setTexts] = useState<string[]>([""]);
  const [span, setSpan] = useState(10);
  useEffect(() => {
    import("mathjs").then(setMath, () => setMath(null));
  }, []);

  const lines: Line[] = useMemo(() => {
    if (!math) return texts.map((text) => ({ text }));
    const scope = new Map<string, unknown>();
    return texts.map((text) => {
      const src = text.trim().replace(/^y\s*=/, "");
      if (!src) return { text };
      try {
        const node = math.parse(src);
        const usesX = node.filter((n) => math.isSymbolNode(n) && n.name === "x").length > 0;
        if (usesX && !math.isAssignmentNode(node) && !math.isFunctionAssignmentNode(node)) {
          const code = node.compile();
          return { text, fn: (x: number) => Number(code.evaluate(new Map([...scope, ["x", x]]))) };
        }
        const v = node.compile().evaluate(scope);
        if (typeof v === "function") return { text, fn: (x: number) => Number(v(x)) };
        return { text, value: math.format(v, { precision: 10 }) };
      } catch (e) {
        return { text, error: e instanceof Error ? e.message : "Can't evaluate" };
      }
    });
  }, [math, texts]);

  const px = (x: number) => ((x + span) / (2 * span)) * W;
  const py = (y: number) => H / 2 - y * (W / (2 * span)); // same scale on both axes
  const paths = lines
    .filter((l) => l.fn)
    .map((l) => {
      let d = "";
      let pen = false;
      for (let i = 0; i <= 400; i++) {
        const x = -span + (2 * span * i) / 400;
        let y = NaN;
        try {
          y = l.fn!(x);
        } catch {
          /* outside the domain */
        }
        if (!Number.isFinite(y) || Math.abs(y) > span * 50) {
          pen = false;
          continue;
        }
        d += `${pen ? "L" : "M"}${px(x).toFixed(1)},${py(y).toFixed(1)}`;
        pen = true;
      }
      return d;
    });
  const colors = ["#0b5c6b", "#c2410c", "#7c3aed", "#15803d"];

  return (
    <div className="space-y-2 p-3 text-sm">
      {lines.map((l, i) => (
        <div key={i}>
          <input
            aria-label={`Expression ${i + 1}`}
            value={l.text}
            onChange={(e) => setTexts((t) => t.map((v, j) => (j === i ? e.target.value : v)))}
            onKeyDown={(e) => e.key === "Enter" && setTexts((t) => [...t.slice(0, i + 1), "", ...t.slice(i + 1)])}
            placeholder={i === 0 ? "e.g. 3*(4-1)^2, y = x^2 - 4, a = 5" : ""}
            className="w-full rounded border border-slate-300 px-2 py-1 font-mono"
            style={l.fn ? { borderLeft: `4px solid ${colors[lines.slice(0, i).filter((p) => p.fn).length % 4]}` } : undefined}
          />
          {l.value !== undefined && <p className="text-right font-mono text-slate-700">= {l.value}</p>}
          {l.error && <p className="text-xs text-red-700">{l.error}</p>}
        </div>
      ))}
      {!math && <p className="text-slate-500">Loading calculator…</p>}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded border border-slate-200 bg-white" role="img" aria-label="Graph">
        {Array.from({ length: 2 * span + 1 }, (_, i) => i - span).map((t) => (
          <g key={t} stroke="#e2e8f0" strokeWidth={t === 0 ? 0 : 0.5}>
            <line x1={px(t)} x2={px(t)} y1={0} y2={H} />
            <line x1={0} x2={W} y1={py(t)} y2={py(t)} />
          </g>
        ))}
        <line x1={0} x2={W} y1={py(0)} y2={py(0)} stroke="#64748b" />
        <line x1={px(0)} x2={px(0)} y1={0} y2={H} stroke="#64748b" />
        {paths.map((d, i) => <path key={i} d={d} fill="none" stroke={colors[i % 4]} strokeWidth={1.8} />)}
      </svg>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>x from −{span} to {span}</span>
        <span className="space-x-2">
          <button type="button" onClick={() => setSpan((s) => Math.max(2, Math.round(s / 2)))} className="rounded border px-2">Zoom in</button>
          <button type="button" onClick={() => setSpan((s) => Math.min(200, s * 2))} className="rounded border px-2">Zoom out</button>
        </span>
      </div>
    </div>
  );
}

export function Calculator({ onClose }: { onClose: () => void }) {
  return (
    <aside
      aria-label="Calculator"
      className="fixed left-4 top-20 z-30 flex w-[360px] flex-col overflow-auto rounded-lg border border-slate-300 bg-white shadow-xl"
      style={{ resize: "both", maxHeight: "80vh" }}
    >
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-100 px-3 py-1.5">
        <span className="text-sm font-semibold">Calculator</span>
        <button type="button" onClick={onClose} aria-label="Close calculator" className="px-1 text-lg leading-none">×</button>
      </div>
      {DESMOS_KEY ? <Desmos apiKey={DESMOS_KEY} /> : <Fallback />}
    </aside>
  );
}
