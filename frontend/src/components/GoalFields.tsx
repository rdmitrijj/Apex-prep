import type { ChangeEvent } from "react";
import type { GoalsForm } from "../api/auth";

const input = "mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:outline-2 focus:outline-brand-500";
const localToday = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in the user's time zone

export function GoalFields({ value, onChange }: { value: GoalsForm; onChange: (v: GoalsForm) => void }) {
  const set = (k: keyof GoalsForm) => (e: ChangeEvent<HTMLInputElement>) => onChange({ ...value, [k]: e.target.value });
  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-semibold">Your SAT goal</legend>
      <label className="block">
        <span className="text-sm font-medium">Test date</span>
        <input type="date" required min={localToday()} value={value.test_date} onChange={set("test_date")} className={input} />
      </label>
      <label className="block">
        <span className="text-sm font-medium">Target total score</span>
        <input type="number" required min={400} max={1600} step={10} placeholder="e.g. 1400" value={value.target_total} onChange={set("target_total")} className={input} />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-sm font-medium">Math minimum</span>
          <input type="number" min={200} max={800} step={10} placeholder="optional" value={value.target_math} onChange={set("target_math")} className={input} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Reading and Writing minimum</span>
          <input type="number" min={200} max={800} step={10} placeholder="optional" value={value.target_rw} onChange={set("target_rw")} className={input} />
        </label>
      </div>
      <p className="text-xs text-slate-500">
        Add a section minimum if a university asks for one. Your study plan and weakness training lean toward the section your goals need more from.
      </p>
    </fieldset>
  );
}
