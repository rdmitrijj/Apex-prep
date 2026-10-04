import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { rebuildPlan, usePlan, type Plan, type PlanTask } from "../api/exam";
import { Shell } from "../components/Shell";

const PHASE: Record<Plan["phase"], string> = {
  build: "Build phase: one full exam a week, daily work on your weakest skills.",
  sharpen: "Sharpen phase: two exams a week (Math on Hard midweek, a full test on Saturday).",
  taper: "Taper: no more full exams. Light review, rest, and sleep.",
};

export function TaskItem({ t }: { t: PlanTask }) {
  return (
    <li className="flex items-start gap-3">
      <span aria-label={t.done ? "Done" : t.done === false ? "Not done yet" : undefined} className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-xs ${t.done ? "border-emerald-600 bg-emerald-600 text-white" : "border-slate-300"}`}>
        {t.done ? "✓" : ""}
      </span>
      <span className="flex-1">
        <Link to={t.link} className="font-medium text-brand-700 hover:underline">{t.title}</Link>
        {t.minutes > 0 && <span className="text-sm text-slate-500"> · {t.minutes} min</span>}
        <span className="block text-sm text-slate-600">{t.detail}</span>
      </span>
    </li>
  );
}

function Day({ d, today }: { d: Plan["days"][number]; today: string }) {
  return (
    <li className={`rounded-xl bg-white p-4 shadow-sm ring-1 ${d.date === today ? "ring-2 ring-brand-500" : "ring-slate-200"}`}>
      <p className="mb-2 flex justify-between text-sm">
        <span className="font-semibold">{dayName(d.date)}{d.date === today && " · today"}</span>
        <span className="text-slate-500">{d.days_left === 0 ? "Test day" : `${d.days_left} days to go`}</span>
      </p>
      <ul className="space-y-2">{d.tasks.map((t) => <TaskItem key={t.id} t={t} />)}</ul>
    </li>
  );
}

export const dayName = (iso: string) => new Date(iso + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" });

export function PlanPage() {
  const plan = usePlan();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const rebuild = () => {
    setBusy(true);
    rebuildPlan().then((p) => qc.setQueryData(["plan"], p)).finally(() => setBusy(false));
  };
  if (plan.isPending) return <Shell><p className="text-slate-500">Loading your plan…</p></Shell>;
  if (plan.isError) return <Shell><p role="alert" className="text-red-700">Couldn't load your plan.</p></Shell>;
  const p = plan.data;
  const past = p.days.filter((d) => d.date < p.today);
  const upcoming = p.days.filter((d) => d.date >= p.today);
  return (
    <Shell>
      <div className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold">This week's plan</h1>
            <p className="text-slate-600">{PHASE[p.phase]}</p>
          </div>
          <button onClick={rebuild} disabled={busy} className="rounded-md border border-brand-700 px-4 py-1.5 text-sm text-brand-700 hover:bg-brand-50 disabled:opacity-50">
            {busy ? "Rebuilding…" : "Rebuild from my latest weaknesses"}
          </button>
        </div>
        <p className="text-sm text-slate-600">
          Focus skills this week: {p.focus.map((f) => f.name).join(", ")}. Tasks tick themselves off as you practise (15 training or 8 drill answers in a day, or a finished exam). The plan refreshes every Monday.
        </p>
        {past.length > 0 && (
          <details className="rounded-xl bg-white p-4 text-sm shadow-sm ring-1 ring-slate-200">
            <summary className="cursor-pointer text-slate-600">Earlier this week ({past.length} {past.length === 1 ? "day" : "days"})</summary>
            <ol className="mt-3 space-y-3">{past.map((d) => <Day key={d.date} d={d} today={p.today} />)}</ol>
          </details>
        )}
        <ol className="space-y-3">{upcoming.map((d) => <Day key={d.date} d={d} today={p.today} />)}</ol>
        {upcoming.length < 3 && p.days[p.days.length - 1]?.days_left > 0 && <p className="text-sm text-slate-500">Next week's plan is built on Monday from your latest results.</p>}
      </div>
    </Shell>
  );
}
