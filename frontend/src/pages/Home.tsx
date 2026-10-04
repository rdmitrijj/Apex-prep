import { useState } from "react";
import { Link } from "react-router-dom";
import { useSkills } from "../api/drill";
import { SECTION_NAME, fmtDate, useExams, useOfficialScores, usePlan, useWeaknesses } from "../api/exam";
import { MasteryHeatmap } from "../components/MasteryHeatmap";
import { ScoreTrend, type TrendPoint } from "../components/ScoreTrend";
import { Shell } from "../components/Shell";
import { TaskItem } from "./PlanPage";
import { WeaknessList } from "../components/WeaknessList";

const TEST_DAY = new Date("2026-12-05T08:00:00");
const GOALS = [
  { label: "Total", key: "Total", target: 1350, max: 1600 },
  { label: "Math", key: "Math", target: 700, max: 800 },
  { label: "Stretch total", key: "Total", target: 1550, max: 1600 },
] as const;

const card = "rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200";

export function Home() {
  const [days] = useState(() => Math.max(0, Math.ceil((TEST_DAY.getTime() - Date.now()) / 86_400_000)));
  const exams = useExams();
  const official = useOfficialScores();
  const weak = useWeaknesses(100);
  const skills = useSkills();
  const plan = usePlan();
  const done = exams.data?.filter((e) => e.status === "completed") ?? [];
  const active = exams.data?.find((e) => e.status === "in_progress");
  // Latest estimate per section, from any finished exam (section-only exams count too).
  const rw = done.find((e) => e.rw_score !== null)?.rw_score ?? null;
  const math = done.find((e) => e.math_score !== null)?.math_score ?? null;
  const now = { Total: rw !== null && math !== null ? rw + math : null, Math: math };
  const fresh = exams.isSuccess && official.isSuccess && done.length === 0 && official.data.scores.length === 0;
  const today = plan.data?.days.find((d) => d.date === plan.data.today);
  const trend: TrendPoint[] = [
    ...done.map((e) => ({ date: e.completed_at ?? e.created_at, rw: e.rw_score, math: e.math_score, official: false })),
    ...(official.data?.scores ?? []).map((o) => ({ date: o.taken_on + "T12:00:00", rw: o.rw, math: o.math, official: true })),
  ];

  return (
    <Shell>
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          <section className={card}>
            <p className="text-sm uppercase tracking-wide text-slate-500">Test day · 5 Dec 2026</p>
            <p className="mt-1 text-4xl font-bold text-brand-700">{days} days left</p>
          </section>
          <section className={`${card} md:col-span-2`}>
            <p className="mb-3 text-sm uppercase tracking-wide text-slate-500">Latest estimate vs. Aalto bar (and 1550 stretch)</p>
            {GOALS.map((g) => {
              const v = now[g.key];
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

        {fresh && (
          <section className="rounded-xl bg-brand-50 p-6 ring-1 ring-brand-100">
            <h2 className="text-lg font-semibold">Start with a diagnostic</h2>
            <p className="mt-1 text-slate-700">
              Everything here adapts to where you stand, so measure that first. Either take a full in-app practice exam (2 h 24 min with the break), or, if you've just taken an official practice test, log its score.
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <Link to="/exam" className="rounded-md bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600">Take the diagnostic exam</Link>
              <Link to="/exam#official" className="rounded-md border border-brand-700 px-4 py-2 font-medium text-brand-700 hover:bg-white">Log an official score</Link>
            </div>
          </section>
        )}

        {active && (
          <Link to={`/exam/${active.id}`} className="block rounded-xl bg-amber-50 p-4 ring-1 ring-amber-200 hover:ring-amber-400">
            Exam in progress: {active.sections.map((s) => SECTION_NAME[s]).join(" + ")}. <span className="font-semibold text-brand-700">Resume →</span>
          </Link>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <section className={card}>
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="font-semibold">Today</h2>
              <Link to="/plan" className="text-sm text-brand-700 hover:underline">Whole week →</Link>
            </div>
            {plan.isPending && <p className="text-sm text-slate-500">Loading…</p>}
            {today ? <ul className="space-y-3">{today.tasks.map((t) => <TaskItem key={t.id} t={t} />)}</ul> : plan.isSuccess && <p className="text-sm text-slate-500">Nothing planned.</p>}
          </section>
          <section className={card}>
            <div className="flex items-baseline justify-between">
              <h2 className="font-semibold">Top weaknesses</h2>
              <Link to="/training" className="text-sm text-brand-700 hover:underline">Train these →</Link>
            </div>
            {weak.data && <WeaknessList rows={weak.data.slice(0, 5)} />}
          </section>
        </div>

        <section className={card}>
          <h2 className="mb-2 font-semibold">Score trend</h2>
          {trend.length ? <ScoreTrend points={trend} /> : <p className="text-sm text-slate-500">Your exam estimates and official scores will appear here.</p>}
          {done.length > 0 && (
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer text-slate-600">Show as table</summary>
              <ul className="mt-1 divide-y divide-slate-100">
                {done.map((e) => (
                  <li key={e.id}>
                    <Link to={`/exam/${e.id}/results`} className="flex justify-between py-1.5 hover:bg-slate-50">
                      <span>{fmtDate(e.completed_at ?? e.created_at)} · <span className="capitalize">{e.difficulty}</span></span>
                      <span className="font-mono">
                        {e.rw_score !== null && `R&W ${e.rw_score} `}
                        {e.math_score !== null && `Math ${e.math_score}`}
                      </span>
                    </Link>
                  </li>
                ))}
                {official.data?.scores.map((o) => (
                  <li key={`o${o.id}`} className="flex justify-between py-1.5">
                    <span>{fmtDate(o.taken_on)} · official {o.kind === "real" ? "test" : "practice test"}</span>
                    <span className="font-mono">R&W {o.rw} Math {o.math}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>

        <section className={card}>
          <h2 className="mb-1 font-semibold">Mastery by skill</h2>
          <p className="mb-3 text-sm text-slate-600">Each square is a sub-skill: your expected chance of getting a medium question right. Hover or focus a square for details.</p>
          {weak.data && skills.data && <MasteryHeatmap rows={weak.data} skills={skills.data} />}
        </section>
      </div>
    </Shell>
  );
}
