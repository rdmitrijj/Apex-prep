import type { WeaknessRow } from "../api/exam";

export function WeaknessList({ rows }: { rows: WeaknessRow[] }) {
  return (
    <ol className="divide-y divide-slate-100">
      {rows.map((w, i) => (
        <li key={w.skill_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2">
          <span className="w-6 text-slate-500">{i + 1}.</span>
          <span className="flex-1">
            {w.name} <span className="text-xs text-slate-500">{w.section === "RW" ? "R&W" : "Math"}</span>
            <span className="block text-sm text-amber-700">{w.reasons.join(" · ")}</span>
          </span>
          <span className="text-right text-sm tabular-nums text-slate-600">
            {w.attempts ? `${w.correct}/${w.attempts} correct` : "—"}
            {w.avg_seconds !== null && <span className="block text-xs">{Math.round(w.avg_seconds)} s avg (test pace {Math.round(w.target_seconds)} s)</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}
