import { useState } from "react";
import type { SkillNode } from "../api/drill";
import type { WeaknessRow } from "../api/exam";

// Reference sequential blue ramp, steps 100-700 (light = low mastery, dark = high).
const RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];
const UNTRIED = "#f0efec";

const color = (m: number) => RAMP[Math.min(RAMP.length - 1, Math.max(0, Math.floor(m * RAMP.length)))];

// One cell per sub-skill, rows per domain: mastery = expected chance on a medium question.
export function MasteryHeatmap({ rows, skills }: { rows: WeaknessRow[]; skills: SkillNode[] }) {
  const [focus, setFocus] = useState<WeaknessRow | null>(null);
  const bySkill = new Map(rows.map((r) => [r.skill_id, r]));
  const domains = skills.filter((s) => s.level === "domain");
  const leaves = skills.filter((s) => s.level === "subskill");

  return (
    <figure className="space-y-3">
      {(["RW", "MATH"] as const).map((sec) => (
        <div key={sec} className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{sec === "RW" ? "Reading and Writing" : "Math"}</p>
          {domains.filter((d) => d.section === sec).map((d) => (
            <div key={d.id} className="flex items-center gap-3">
              <span className="w-40 shrink-0 truncate text-xs text-slate-600" title={d.name}>{d.name}</span>
              <div className="flex flex-wrap gap-0.5">
                {leaves.filter((l) => l.id.startsWith(d.id + ".")).map((l) => {
                  const r = bySkill.get(l.id);
                  const tried = !!r && r.attempts > 0;
                  const label = `${l.name}: ${tried ? `${Math.round(r!.mastery * 100)}% mastery, ${r!.correct}/${r!.attempts} correct` : "not tried yet"}`;
                  return (
                    <button
                      key={l.id}
                      type="button"
                      aria-label={label}
                      title={label}
                      onPointerEnter={() => r && setFocus(r)}
                      onFocus={() => r && setFocus(r)}
                      className="h-5 w-5 rounded-[3px] outline-offset-1 hover:outline hover:outline-2 hover:outline-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900"
                      style={{ background: tried ? color(r!.mastery) : UNTRIED }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ))}
      <figcaption className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <span className="flex items-center gap-1.5">
          Low
          <span className="h-2.5 w-28 rounded-sm" style={{ background: `linear-gradient(to right, ${RAMP[0]}, ${RAMP[6]}, ${RAMP[12]})` }} />
          High mastery
        </span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm ring-1 ring-slate-300" style={{ background: UNTRIED }} /> Not tried</span>
        <span className="min-h-4 text-slate-900" aria-live="polite">
          {focus && (
            <>
              <strong className="tabular-nums">{focus.attempts ? `${Math.round(focus.mastery * 100)}%` : "—"}</strong> {focus.name}
              {focus.attempts > 0 && <span className="text-slate-500"> · {focus.correct}/{focus.attempts} correct</span>}
            </>
          )}
        </span>
      </figcaption>
    </figure>
  );
}
