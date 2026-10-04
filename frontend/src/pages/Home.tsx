import { useState } from "react";
import { Link } from "react-router-dom";
import { SECTION_NAME, fmtDate, useExams, useWeaknesses } from "../api/exam";
import { Shell } from "../components/Shell";
import { WeaknessList } from "./Training";

const TEST_DAY = new Date("2026-12-05T08:00:00");
const GOALS = [
  { label: "Total", target: 1350, max: 1600 },
  { label: "Math", target: 700, max: 800 },
];

const card = "rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200";

export function Home() {
  const [days] = useState(() => Math.max(0, Math.ceil((TEST_DAY.getTime() - Date.now()) / 86_400_000)));
  const exams = useExams();
  const weak = useWeaknesses(5);
  const done = exams.data?.filter((e) => e.status === "completed") ?? [];
  const active = exams.data?.find((e) => e.status === "in_progress");
  // Latest estimate per section, from any finished exam (section-only exams count too).
  const rw = done.find((e) => e.rw_score !== null)?.rw_score ?? null;
  const math = done.find((e) => e.math_score !== null)?.math_score ?? null;
  const now = { Total: rw !== null && math !== null ? rw + math : null, Math: math };

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          <section className={card}>
            <p className="text-sm uppercase tracking-wide text-slate-500">Test day · 5 Dec 2026</p>
            <p className="mt-1 text-4xl font-bold text-brand-700">{days} days left</p>
          </section>
          <section className={`${card} md:col-span-2`}>
            <p className="mb-3 text-sm uppercase tracking-wide text-slate-500">Latest estimate vs. Aalto bar</p>
            {GOALS.map((g) => {
              const v = now[g.label as keyof typeof now];
              return (
                <div key={g.label} className="mb-2">
                  <div className="flex justify-between text-sm">
                    <span>{g.label}</span>
                    <span className="tabular-nums">{v ?? "—"} / {g.target}</span>
                  </div>
                  <div className="relative h-2 rounded bg-slate-200">
                    {v !== null && <div className={`h-2 rounded ${v >= g.target ? "bg-emerald-600" : "bg-brand-500"}`} style={{ width: `${(100 * v) / g.max}%` }} />}
                    <div className="absolute -top-1 h-4 w-0.5 bg-slate-900" style={{ left: `${(100 * g.target) / g.max}%` }} title={`Target ${g.target}`} />
                  </div>
                </div>
              );
            })}
            {rw === null && math === null && <p className="text-sm text-slate-500">Take a practice exam to get your first estimate.</p>}
          </section>
        </div>

        {active && (
          <Link to={`/exam/${active.id}`} className="block rounded-xl bg-amber-50 p-4 ring-1 ring-amber-200 hover:ring-amber-400">
            Exam in progress: {active.sections.map((s) => SECTION_NAME[s]).join(" + ")}. <span className="font-semibold text-brand-700">Resume →</span>
          </Link>
        )}

        <div className="grid gap-4 md:grid-cols-3">
          {[
            { to: "/exam", name: "Practice Exam", desc: "Full adaptive test or one section, timed like the real thing." },
            { to: "/drill", name: "Topic Drill", desc: "Pick topics and a difficulty, get instant feedback with worked solutions." },
            { to: "/training", name: "Weakness Training", desc: "Questions aimed at your misses, slow skills, and gaps." },
          ].map((c) => (
            <Link key={c.to} to={c.to} className={`${card} hover:ring-brand-500`}>
              <p className="text-lg font-semibold">{c.name}</p>
              <p className="text-sm text-slate-600">{c.desc}</p>
            </Link>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <section className={card}>
            <div className="flex items-baseline justify-between">
              <h2 className="font-semibold">Top weaknesses</h2>
              <Link to="/training" className="text-sm text-brand-700 hover:underline">Train these →</Link>
            </div>
            {weak.data && <WeaknessList rows={weak.data} />}
          </section>
          <section className={card}>
            <h2 className="font-semibold">Score history</h2>
            {done.length === 0 && <p className="text-sm text-slate-500">No finished exams yet.</p>}
            <ul className="divide-y divide-slate-100 text-sm">
              {done.slice(0, 8).map((e) => (
                <li key={e.id}>
                  <Link to={`/exam/${e.id}/results`} className="flex justify-between py-2 hover:bg-slate-50">
                    <span>{fmtDate(e.completed_at ?? e.created_at)} · <span className="capitalize">{e.difficulty}</span></span>
                    <span className="font-mono">
                      {e.rw_score !== null && `R&W ${e.rw_score} `}
                      {e.math_score !== null && `Math ${e.math_score}`}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </Shell>
  );
}
