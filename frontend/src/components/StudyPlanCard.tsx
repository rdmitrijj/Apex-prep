import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { checkPlan, useStudyPlan } from "../api/pt5";

// The fixed 5-day plan to the weekend mock (seed/pt5/plan.json); shown only to users with PT5 imports.
export function StudyPlanCard() {
  const plan = useStudyPlan();
  const qc = useQueryClient();
  if (!plan.data?.visible) return null;
  const today = new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD, local time
  const toggle = (key: string, done: boolean) => {
    qc.setQueryData(["pt5-plan"], { ...plan.data!, days: plan.data!.days.map((d) => ({ ...d, items: d.items.map((i) => (i.key === key ? { ...i, done } : i)) })) });
    checkPlan(key, done).catch(() => void qc.invalidateQueries({ queryKey: ["pt5-plan"] }));
  };
  return (
    <section className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h2 className="mb-3 font-semibold">{plan.data.title}</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {plan.data.days.map((d) => (
          <div key={d.date} className={`rounded-lg p-3 ring-1 ${d.date === today ? "bg-brand-50 ring-brand-300" : "ring-slate-200"}`}>
            <h3 className="mb-2 text-sm font-semibold">{d.title}{d.date === today && " · today"}</h3>
            <ul className="space-y-1.5 text-sm">
              {d.items.map((i) => (
                <li key={i.key} className="flex items-start gap-2">
                  <input type="checkbox" id={`plan-${i.key}`} checked={i.done} onChange={(e) => toggle(i.key, e.target.checked)} className="mt-1" />
                  <label htmlFor={`plan-${i.key}`} className={i.done ? "text-slate-500 line-through" : ""}>
                    {i.link ? <Link to={i.link} className="underline">{i.text}</Link> : i.text}
                  </label>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
