import { useState } from "react";

// Categorical slots 1-2 of the reference palette (validated: CVD ΔE 24.7, contrast ≥ 3:1).
const COLOR = { RW: "#2a78d6", MATH: "#eb6834" } as const;
const NAME = { RW: "R&W", MATH: "Math" } as const;
const W = 640;
const H = 240;
const PAD = { l: 40, r: 56, t: 12, b: 28 };
const DAY = 86_400_000;

export type TrendPoint = { date: string; rw: number | null; math: number | null; official: boolean };

const fmt = (t: number) => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short" });
// Plot by calendar day (local noon), so results from the same day share one x and one tooltip.
const dayOf = (iso: string) => {
  const d = new Date(iso);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12).getTime();
};

// Section estimates over time (one 200-800 axis), official scores as hollow rings, Math 700 target.
export function ScoreTrend({ points, target = 700 }: { points: TrendPoint[]; target?: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const pts = points
    .map((p) => ({ ...p, t: dayOf(p.date), exact: new Date(p.date).getTime() }))
    .sort((a, b) => a.exact - b.exact);
  if (!pts.length) return null;
  const values = pts.flatMap((p) => [p.rw, p.math]).filter((v): v is number => v !== null);
  const yMin = Math.max(200, Math.min(600, Math.floor((Math.min(...values) - 40) / 100) * 100));
  const t0 = pts[0].t - 3 * DAY;
  const t1 = pts[pts.length - 1].t + 3 * DAY;
  const x = (t: number) => PAD.l + ((t - t0) / (t1 - t0)) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + ((800 - v) / (800 - yMin)) * (H - PAD.t - PAD.b);
  const ticks = Array.from({ length: (800 - yMin) / 100 + 1 }, (_, i) => yMin + i * 100);
  const dates = [...new Set(pts.map((p) => p.t))];

  const line = (key: "rw" | "math") =>
    pts
      .filter((p) => !p.official && p[key] !== null)
      .map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p[key]!).toFixed(1)}`)
      .join("");
  const last = (key: "rw" | "math") => [...pts].reverse().find((p) => !p.official && p[key] !== null);
  // End-of-line labels: keep at least 13px apart vertically so they never overprint.
  const ends = (["rw", "math"] as const)
    .map((k) => ({ k, p: last(k) }))
    .filter((e): e is { k: "rw" | "math"; p: NonNullable<ReturnType<typeof last>> } => !!e.p)
    .map((e) => ({ ...e, y: y(e.p[e.k]!) }))
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 13);

  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const t = t0 + ((((e.clientX - box.left) / box.width) * W - PAD.l) / (W - PAD.l - PAD.r)) * (t1 - t0);
    setHover(dates.reduce((best, d) => (Math.abs(d - t) < Math.abs(best - t) ? d : best), dates[0]));
  };
  const atHover = hover === null ? [] : pts.filter((p) => p.t === hover);

  return (
    <figure className="space-y-2">
      <div className="flex flex-wrap gap-4 text-xs text-slate-600" aria-hidden>
        {(["RW", "MATH"] as const).map((s) => (
          <span key={s} className="flex items-center gap-1.5">
            <svg width="16" height="8"><line x1="0" x2="16" y1="4" y2="4" stroke={COLOR[s]} strokeWidth="2" /></svg>
            {NAME[s]} estimate
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <svg width="12" height="12"><circle cx="6" cy="6" r="4" fill="white" stroke="#52514e" strokeWidth="2" /></svg>
          Official score
        </span>
        <span className="flex items-center gap-1.5">
          <svg width="16" height="8"><line x1="0" x2="16" y1="4" y2="4" stroke="#52514e" strokeDasharray="3 3" /></svg>
          Math target
        </span>
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Score trend: ${pts.length} results from ${fmt(pts[0].t)} to ${fmt(pts[pts.length - 1].t)}`}>
          {ticks.map((v) => (
            <g key={v}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="#e7e5e0" />
              <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" className="fill-slate-500 text-[11px]">{v}</text>
            </g>
          ))}
          <line x1={PAD.l} x2={W - PAD.r} y1={y(target)} y2={y(target)} stroke="#52514e" strokeDasharray="4 4" />
          <text x={PAD.l + 4} y={y(target) - 4} className="fill-slate-600 text-[11px]">Math {target}</text>
          {[...new Set([dates[0], dates[dates.length - 1]])].map((t) => (
            <text key={t} x={x(t)} y={H - 8} textAnchor="middle" className="fill-slate-500 text-[11px]">{fmt(t)}</text>
          ))}
          {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={H - PAD.b} stroke="#9a9893" />}
          {(["rw", "math"] as const).map((k) => {
            const s = k === "rw" ? "RW" : "MATH";
            return (
              <g key={k}>
                <path d={line(k)} fill="none" stroke={COLOR[s]} strokeWidth="2" strokeLinejoin="round" />
                {pts.filter((p) => p[k] !== null).map((p, i) => (
                  <circle key={i} cx={x(p.t)} cy={y(p[k]!)} r={p.official ? 5 : 4} fill={p.official ? "white" : COLOR[s]} stroke={p.official ? COLOR[s] : "white"} strokeWidth="2" />
                ))}
              </g>
            );
          })}
          {ends.map((e) => (
            <text key={e.k} x={x(e.p.t) + 8} y={e.y + 4} className="fill-slate-700 text-[11px]">{NAME[e.k === "rw" ? "RW" : "MATH"]} {e.p[e.k]}</text>
          ))}
          <rect x={PAD.l} y={PAD.t} width={W - PAD.l - PAD.r} height={H - PAD.t - PAD.b} fill="transparent" onPointerMove={onMove} onPointerLeave={() => setHover(null)} />
        </svg>
        {hover !== null && (
          <div className="pointer-events-none absolute top-2 rounded-md bg-white px-3 py-2 text-xs shadow-lg ring-1 ring-slate-200" style={{ left: `${Math.min(70, (x(hover) / W) * 100)}%` }}>
            <p className="mb-1 text-slate-500">{fmt(hover)}</p>
            {atHover.map((p, i) => (
              <div key={i}>
                {(["rw", "math"] as const).filter((k) => p[k] !== null).map((k) => (
                  <p key={k} className="flex items-center gap-2">
                    <svg width="12" height="6"><line x1="0" x2="12" y1="3" y2="3" stroke={COLOR[k === "rw" ? "RW" : "MATH"]} strokeWidth="2" /></svg>
                    <strong className="tabular-nums text-slate-900">{p[k]}</strong>
                    <span className="text-slate-500">{NAME[k === "rw" ? "RW" : "MATH"]}{p.official ? " (official)" : ""}</span>
                  </p>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </figure>
  );
}
