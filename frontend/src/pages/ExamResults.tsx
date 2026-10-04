import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { fmtDate, SECTION_NAME, TARGET_SECONDS, useExamResults, type ExamResults as Results, type ReviewItem, type Section } from "../api/exam";
import { QuestionView } from "../components/QuestionView";
import { Shell } from "../components/Shell";

const TARGETS = { total: 1350, MATH: 700 };
type Filter = "all" | "wrong" | "flagged" | "slow";

function ScoreCard({ label, score, target, margin }: { label: string; score: number; target?: number; margin?: number }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-4xl font-bold text-brand-700">
        {score}
        {margin !== undefined && <span className="ml-2 text-lg font-normal text-slate-500" title="One standard deviation: about 2 in 3 chance the true score is in this range">±{margin}</span>}
      </p>
      {target && (
        <p className={`text-sm ${score >= target ? "text-emerald-700" : "text-slate-600"}`}>
          {score >= target ? `At or above your ${target} target` : `${target - score} below your ${target} target`}
        </p>
      )}
    </div>
  );
}

function Bar({ correct, total }: { correct: number; total: number }) {
  const pct = total ? Math.round((100 * correct) / total) : 0;
  const tone = pct >= 80 ? "bg-emerald-600" : pct >= 60 ? "bg-amber-500" : "bg-red-600";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-32 rounded bg-slate-200"><div className={`h-2 rounded ${tone}`} style={{ width: `${pct}%` }} /></div>
      <span className="w-20 text-right text-sm tabular-nums">{correct}/{total}</span>
    </div>
  );
}

function Breakdown({ r, section }: { r: Results; section: Section }) {
  const rows = r.breakdown.filter((b) => b.section === section);
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h3 className="mb-2 font-semibold">{SECTION_NAME[section]}</h3>
      <ul className="space-y-1">
        {rows.map((b) => (
          <li key={b.id} className={`flex items-center justify-between gap-2 ${b.level === "domain" ? "pt-2 font-medium" : "pl-4 text-sm text-slate-700"}`}>
            <span>{b.name}</span>
            <Bar correct={b.correct} total={b.total} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function Pace({ items, section }: { items: ReviewItem[]; section: Section }) {
  const own = items.filter((i) => i.section === section);
  if (!own.length) return null;
  const avg = own.reduce((s, i) => s + i.time_ms, 0) / own.length / 1000;
  const target = TARGET_SECONDS[section];
  return (
    <p className="text-sm text-slate-600">
      {SECTION_NAME[section]}: {avg.toFixed(0)} s per question on average (test pace {target.toFixed(0)} s).
      {avg > target * 1.1 && <span className="text-red-700"> Too slow.</span>}
    </p>
  );
}

function Row({ item, n }: { item: ReviewItem; n: number }) {
  const [open, setOpen] = useState(false);
  const status = item.answer === null ? "Omitted" : item.correct ? "Correct" : "Incorrect";
  const tone = item.correct ? "text-emerald-700" : "text-red-700";
  return (
    <li className="py-2">
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 text-left text-sm hover:bg-slate-50">
        <span className="w-10 text-slate-500">#{n}</span>
        <span className={`w-20 font-medium ${tone}`}>{status}</span>
        <span className="flex-1">{item.question.skill_name}</span>
        <span className="hidden w-16 capitalize text-slate-500 sm:inline">{item.difficulty}</span>
        <span className="w-14 text-right tabular-nums text-slate-600">{Math.round(item.time_ms / 1000)} s</span>
        <span className="w-6">{item.flagged ? "⚑" : ""}</span>
      </button>
      {open && (
        <div className="mt-3 rounded-lg p-4 ring-1 ring-slate-200">
          <p className="mb-2 text-xs text-slate-500">
            {item.module} · Question {item.position}
            {item.pretest && " · unscored (pretest)"}
            {item.answer && ` · you answered ${item.answer}`}
          </p>
          <QuestionView
            q={item.question}
            given={item.answer}
            busy={false}
            error={null}
            onSubmit={() => {}}
            feedback={{ correct: item.correct, answer: item.key, explanation: item.explanation, rationales: item.rationales }}
          />
        </div>
      )}
    </li>
  );
}

export function ExamResults() {
  const id = Number(useParams().id);
  const res = useExamResults(id);
  const [filter, setFilter] = useState<Filter>("all");
  if (res.isPending) return <Shell><p className="text-slate-500">Loading results…</p></Shell>;
  if (res.isError)
    return <Shell><p role="alert" className="text-red-700">{res.error instanceof ApiError ? res.error.message : "Couldn't load results."}</p></Shell>;
  const r = res.data;
  const both = r.rw_score !== null && r.math_score !== null;
  const slowCut = [...r.items].sort((a, b) => b.time_ms / TARGET_SECONDS[b.section] - a.time_ms / TARGET_SECONDS[a.section])[Math.min(9, r.items.length - 1)];
  const slowRatio = slowCut ? slowCut.time_ms / TARGET_SECONDS[slowCut.section] : Infinity;
  const shown = r.items
    .map((item, i) => ({ item, n: i + 1 }))
    .filter(({ item }) =>
      filter === "wrong" ? !item.correct : filter === "flagged" ? item.flagged : filter === "slow" ? item.time_ms / TARGET_SECONDS[item.section] >= slowRatio && item.time_ms > 0 : true,
    );
  const wrong = r.items.filter((i) => !i.correct && !i.pretest).length;

  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h1 className="text-2xl font-bold">Exam results</h1>
          <span className="text-sm text-slate-500">{fmtDate(r.completed_at ?? r.created_at)} · <span className="capitalize">{r.difficulty}</span></span>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {both && <ScoreCard label="Total (estimate)" score={r.rw_score! + r.math_score!} target={TARGETS.total} margin={Math.round(Math.hypot(r.margins.RW ?? 0, r.margins.MATH ?? 0) / 10) * 10} />}
          {r.rw_score !== null && <ScoreCard label="Reading and Writing" score={r.rw_score} margin={r.margins.RW} />}
          {r.math_score !== null && <ScoreCard label="Math" score={r.math_score} target={TARGETS.MATH} margin={r.margins.MATH} />}
        </div>
        <p className="text-xs text-slate-500">
          Estimates from a Rasch model over the scored questions (pretest questions don't count), mapped to the 200–800 scale{" "}
          {Object.values(r.calibrated_with).some((n) => n)
            ? `calibrated to your official scores (${r.sections.map((s) => `${s === "RW" ? "R&W" : "Math"}: ${r.calibrated_with[s] ?? 0}`).join(", ")}).`
            : "by a default curve."}{" "}
          ± is one standard deviation.{" "}
          {!Object.values(r.calibrated_with).some((n) => n) && <Link to="/exam" className="underline">Log an official practice-test score</Link>}
          {!Object.values(r.calibrated_with).some((n) => n) && " to calibrate."}
        </p>
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-brand-50 p-5 ring-1 ring-brand-100">
          <div>
            <p className="font-semibold">{wrong} scored questions missed</p>
            <Pace items={r.items} section="RW" />
            <Pace items={r.items} section="MATH" />
          </div>
          <Link to="/training" className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">Train my weak spots</Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {r.sections.map((s) => <Breakdown key={s} r={r} section={s} />)}
        </div>
        <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Question review</h2>
            <div className="flex gap-1 text-sm" role="group" aria-label="Filter questions">
              {(["all", "wrong", "flagged", "slow"] as Filter[]).map((f) => (
                <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)} className={`rounded-full px-3 py-1 ${filter === f ? "bg-brand-700 text-white" : "bg-slate-100"}`}>
                  {{ all: "All", wrong: "Incorrect", flagged: "Marked", slow: "Slowest" }[f]}
                </button>
              ))}
            </div>
          </div>
          <ul className="divide-y divide-slate-100">
            {shown.map(({ item, n }) => <Row key={n} item={item} n={n} />)}
          </ul>
          {!shown.length && <p className="text-slate-500">Nothing here.</p>}
        </section>
      </div>
    </Shell>
  );
}
