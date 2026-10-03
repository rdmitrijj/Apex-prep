import type { FigureSpec } from "../api/drill";
import { MathText } from "./MathText";

const W = 440;
const H = 300;
const M = { l: 48, r: 16, t: 16, b: 44 };
const SERIES = ["fill-brand-600 stroke-brand-600", "fill-amber-500 stroke-amber-500", "fill-slate-500 stroke-slate-500", "fill-rose-500 stroke-rose-500"];

const lerp = (v: number, [d0, d1]: [number, number], [r0, r1]: [number, number]) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);

function niceStep(range: number, target = 8) {
  const raw = range / target;
  const p = 10 ** Math.floor(Math.log10(raw || 1));
  return ([1, 2, 5, 10].find((m) => m * p >= raw) ?? 10) * p;
}

function ticks([a, b]: [number, number]) {
  const s = niceStep(b - a);
  const out: number[] = [];
  for (let v = Math.ceil(a / s) * s; v <= b + 1e-9; v += s) out.push(Number(v.toFixed(6)));
  return out;
}

const fmt = (v: number) => (Number.isInteger(v) ? String(v) : String(Number(v.toFixed(2))));

function Axes({ xd, yd, xlabel, ylabel, xticks, cross }: { xd: [number, number]; yd: [number, number]; xlabel?: string; ylabel?: string; xticks?: number[]; cross?: boolean }) {
  const X = (v: number) => lerp(v, xd, [M.l, W - M.r]);
  const Y = (v: number) => lerp(v, yd, [H - M.b, M.t]);
  const x0 = cross && xd[0] <= 0 && xd[1] >= 0 ? X(0) : M.l;
  const y0 = cross && yd[0] <= 0 && yd[1] >= 0 ? Y(0) : H - M.b;
  return (
    <g className="text-[11px]">
      {ticks(yd).map((v) => (
        <g key={`y${v}`}>
          <line x1={M.l} x2={W - M.r} y1={Y(v)} y2={Y(v)} className="stroke-slate-200" />
          <text x={x0 - 4} y={Y(v) + 4} textAnchor="end" className="fill-slate-600">{fmt(v)}</text>
        </g>
      ))}
      {(xticks ?? ticks(xd)).map((v) => (
        <g key={`x${v}`}>
          {!xticks && <line y1={M.t} y2={H - M.b} x1={X(v)} x2={X(v)} className="stroke-slate-200" />}
          <text x={X(v)} y={y0 + 14} textAnchor="middle" className="fill-slate-600">{fmt(v)}</text>
        </g>
      ))}
      <line x1={M.l} x2={W - M.r} y1={y0} y2={y0} className="stroke-slate-700" />
      <line x1={x0} x2={x0} y1={M.t} y2={H - M.b} className="stroke-slate-700" />
      {xlabel && <text x={(M.l + W - M.r) / 2} y={H - 6} textAnchor="middle" className="fill-slate-800 text-xs">{xlabel}</text>}
      {ylabel && <text transform={`translate(12 ${(M.t + H - M.b) / 2}) rotate(-90)`} textAnchor="middle" className="fill-slate-800 text-xs">{ylabel}</text>}
    </g>
  );
}

function Legend({ names }: { names: string[] }) {
  if (names.length < 2) return null;
  return (
    <div className="mt-1 flex flex-wrap justify-center gap-4 text-xs text-slate-700">
      {names.map((n, i) => (
        <span key={n} className="flex items-center gap-1">
          <svg width="12" height="12" aria-hidden><rect width="12" height="12" className={SERIES[i % SERIES.length]} /></svg>
          {n}
        </span>
      ))}
    </div>
  );
}

function Svg({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="mx-auto w-full max-w-[440px]">
      {children}
    </svg>
  );
}

export function Figure({ spec }: { spec: FigureSpec }) {
  const title = "title" in spec && spec.title ? <p className="mb-1 text-center text-sm font-medium">{spec.title}</p> : null;
  switch (spec.kind) {
    case "table":
      return (
        <figure className="my-3 overflow-x-auto">
          {title}
          <table className="mx-auto border-collapse text-sm">
            <thead>
              <tr>{spec.header.map((h, i) => <th key={i} className="border border-slate-400 bg-slate-100 px-3 py-1"><MathText text={h} /></th>)}</tr>
            </thead>
            <tbody>
              {spec.rows.map((r, i) => (
                <tr key={i}>{r.map((c, j) => <td key={j} className="border border-slate-400 px-3 py-1 text-center"><MathText text={c} /></td>)}</tr>
              ))}
            </tbody>
          </table>
        </figure>
      );
    case "bars": {
      const groups = spec.series ?? [{ name: "", values: spec.values ?? [] }];
      const max = Math.max(...groups.flatMap((g) => g.values), 0);
      const yd: [number, number] = [0, max * 1.1 || 1];
      const band = (W - M.l - M.r) / spec.labels.length;
      const bw = (band * 0.7) / groups.length;
      return (
        <figure className="my-3">
          {title}
          <Svg label={`Bar graph${spec.title ? `: ${spec.title}` : ""}`}>
            <Axes xd={[0, 1]} yd={yd} xlabel={spec.xlabel} ylabel={spec.ylabel} xticks={[]} />
            {spec.labels.map((l, i) => (
              <g key={l}>
                {groups.map((g, s) => {
                  const y = lerp(g.values[i], yd, [H - M.b, M.t]);
                  return <rect key={s} x={M.l + band * i + band * 0.15 + bw * s} y={y} width={bw} height={H - M.b - y} className={SERIES[s % SERIES.length]} />;
                })}
                <text x={M.l + band * (i + 0.5)} y={H - M.b + 14} textAnchor="middle" className="fill-slate-600 text-[11px]">{l}</text>
              </g>
            ))}
          </Svg>
          <Legend names={groups.map((g) => g.name)} />
        </figure>
      );
    }
    case "line": {
      const xd: [number, number] = [Math.min(...spec.x), Math.max(...spec.x)];
      const all = spec.series.flatMap((s) => s.values);
      const pad = (Math.max(...all) - Math.min(...all)) * 0.1 || 1;
      const yd: [number, number] = [Math.min(0, Math.min(...all) - pad), Math.max(...all) + pad];
      const X = (v: number) => lerp(v, xd, [M.l, W - M.r]);
      const Y = (v: number) => lerp(v, yd, [H - M.b, M.t]);
      return (
        <figure className="my-3">
          {title}
          <Svg label={`Line graph${spec.title ? `: ${spec.title}` : ""}`}>
            <Axes xd={xd} yd={yd} xlabel={spec.xlabel} ylabel={spec.ylabel} xticks={spec.x} />
            {spec.series.map((s, i) => (
              <g key={s.name} className={SERIES[i % SERIES.length]}>
                <polyline fill="none" strokeWidth={2} points={s.values.map((v, j) => `${X(spec.x[j])},${Y(v)}`).join(" ")} />
                {s.values.map((v, j) => <circle key={j} cx={X(spec.x[j])} cy={Y(v)} r={3} />)}
              </g>
            ))}
          </Svg>
          <Legend names={spec.series.map((s) => s.name)} />
        </figure>
      );
    }
    case "plot": {
      const X = (v: number) => lerp(v, spec.x, [M.l, W - M.r]);
      const Y = (v: number) => lerp(v, spec.y, [H - M.b, M.t]);
      return (
        <figure className="my-3">
          <Svg label="Graph in the xy-plane">
            <defs>
              <clipPath id="plot-area"><rect x={M.l} y={M.t} width={W - M.l - M.r} height={H - M.t - M.b} /></clipPath>
            </defs>
            <Axes xd={spec.x} yd={spec.y} xlabel={spec.xlabel} ylabel={spec.ylabel} cross />
            <g clipPath="url(#plot-area)">
              {spec.polygons?.map((p, i) => <polygon key={i} points={p.map(([a, b]) => `${X(a)},${Y(b)}`).join(" ")} className="fill-brand-100 stroke-brand-700" strokeWidth={2} />)}
              {spec.curves?.map((c, i) => <polyline key={i} fill="none" strokeWidth={2} className="stroke-brand-700" points={c.map(([a, b]) => `${X(a)},${Y(b)}`).join(" ")} />)}
            </g>
            {spec.points?.map(([a, b, label], i) => (
              <g key={i}>
                <circle cx={X(a)} cy={Y(b)} r={4} className="fill-slate-900" />
                {label && <text x={X(a) + 6} y={Y(b) - 6} className="fill-slate-900 text-xs">{label}</text>}
              </g>
            ))}
          </Svg>
        </figure>
      );
    }
    case "shape":
      return <Shape spec={spec} />;
  }
}

function Shape({ spec }: { spec: Extract<FigureSpec, { kind: "shape" }> }) {
  const pts = Object.values(spec.points);
  const ext = [...pts, ...spec.labels.map((l) => l.at), ...(spec.circles ?? []).flatMap((c) => [[c.c[0] - c.r, c.c[1] - c.r], [c.c[0] + c.r, c.c[1] + c.r]] as [number, number][])];
  const xs = ext.map((p) => p[0]);
  const ys = ext.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const pad = 24;
  const k = Math.min((W - 2 * pad) / (x1 - x0 || 1), (H - 2 * pad) / (y1 - y0 || 1));
  const P = ([a, b]: [number, number]): [number, number] => [pad + (a - x0) * k + ((W - 2 * pad) - (x1 - x0) * k) / 2, H - pad - (b - y0) * k - ((H - 2 * pad) - (y1 - y0) * k) / 2];
  const centroid = pts.reduce((s, p) => [s[0] + p[0] / pts.length, s[1] + p[1] / pts.length], [0, 0]);

  const rightMark = (v: string) => {
    const nbrs = spec.segments.filter((s) => s.includes(v)).map((s) => spec.points[s[0] === v ? s[1] : s[0]]);
    if (nbrs.length < 2) return null;
    const o = P(spec.points[v]);
    const unit = (q: [number, number]) => {
      const [dx, dy] = [P(q)[0] - o[0], P(q)[1] - o[1]];
      const n = Math.hypot(dx, dy) || 1;
      return [(dx / n) * 12, (dy / n) * 12];
    };
    const [a, b] = [unit(nbrs[0]), unit(nbrs[1])];
    return <polyline key={`ra-${v}`} fill="none" className="stroke-slate-700" points={`${o[0] + a[0]},${o[1] + a[1]} ${o[0] + a[0] + b[0]},${o[1] + a[1] + b[1]} ${o[0] + b[0]},${o[1] + b[1]}`} />;
  };

  return (
    <figure className="my-3">
      <Svg label="Geometric figure">
        {spec.circles?.map((c, i) => {
          const [cx, cy] = P(c.c);
          return <circle key={i} cx={cx} cy={cy} r={c.r * k} className="fill-none stroke-slate-800" strokeWidth={1.5} />;
        })}
        {spec.segments.map(([a, b]) => {
          const [p, q] = [P(spec.points[a]), P(spec.points[b])];
          return <line key={a + b} x1={p[0]} y1={p[1]} x2={q[0]} y2={q[1]} className="stroke-slate-800" strokeWidth={1.5} />;
        })}
        {spec.right_angles?.map(rightMark)}
        {!spec.hide_points &&
          Object.entries(spec.points).map(([name, p]) => {
            const [sx, sy] = P(p);
            const [dx, dy] = [p[0] - centroid[0], p[1] - centroid[1]];
            const n = Math.hypot(dx, dy) || 1;
            return (
              <g key={name}>
                <circle cx={sx} cy={sy} r={2.5} className="fill-slate-900" />
                <text x={sx + (dx / n) * 14} y={sy - (dy / n) * 14 + 4} textAnchor="middle" className="fill-slate-900 text-sm italic">{name}</text>
              </g>
            );
          })}
        {spec.labels.map((l, i) => {
          const [sx, sy] = P(l.at);
          return <text key={i} x={sx} y={sy + 4} textAnchor="middle" className="fill-slate-900 text-[13px]">{l.text}</text>;
        })}
      </Svg>
    </figure>
  );
}
