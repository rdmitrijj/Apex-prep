import { useState } from "react";
import { Link } from "react-router-dom";
import { trainingNext, useExamMisses, useWeaknesses, type ExamMisses, type Section } from "../api/exam";
import { Shell } from "../components/Shell";
import { WeaknessList } from "../components/WeaknessList";
import { Session } from "./Drill";

type Scope = "exam" | "all";

export function Training() {
  const weak = useWeaknesses(40);
  const misses = useExamMisses();
  const [section, setSection] = useState<Section | null>(null);
  const [count, setCount] = useState(20);
  const [running, setRunning] = useState(false);
  const [picked, setPicked] = useState<Scope | null>(null);
  // Default to last-exam mistakes whenever there are any left to clear.
  const scope: Scope = picked ?? (misses.data?.open.length ? "exam" : "all");
  if (running)
    return (
      <Shell>
        <Session count={count} mode="training" fetchNext={(exclude) => trainingNext({ exclude_ids: exclude, section, last_exam: scope === "exam" })} onDone={() => setRunning(false)} />
      </Shell>
    );
  const rows = (weak.data ?? []).filter((w) => section === null || w.section === section).slice(0, 10);
  const open = (misses.data?.open ?? []).filter((m) => section === null || m.section === section);
  return (
    <Shell>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Weakness Training</h1>
        <p className="text-slate-600">
          {scope === "exam"
            ? `Only the skills you missed in your last practice exam. A skill is cleared once you answer ${misses.data?.clear_streak ?? 15} of its questions correctly in a row; a miss restarts the count.`
            : "Questions come from the skills where you lose the most points: misses, slow answers, and skills you haven't practised lately, weighted by how often they appear on the test (Math counts 1.3× for your 700 target)."}{" "}
          Difficulty adapts so you get about two in three right.
          {weak.data?.every((w) => w.attempts === 0) && <> Take a <Link to="/exam" className="text-brand-700 underline">practice exam</Link> first so this knows where you stand.</>}
        </p>
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm">
            Train
            <select value={scope} onChange={(e) => setPicked(e.target.value as Scope)} className="ml-2 rounded border border-slate-300 px-2 py-1">
              <option value="exam">Mistakes from my last exam</option>
              <option value="all">All weaknesses</option>
            </select>
          </label>
          <label className="text-sm">
            Focus
            <select value={section ?? ""} onChange={(e) => setSection((e.target.value || null) as Section | null)} className="ml-2 rounded border border-slate-300 px-2 py-1">
              <option value="">Both sections</option>
              <option value="MATH">Math</option>
              <option value="RW">Reading and Writing</option>
            </select>
          </label>
          <label className="text-sm">
            Questions
            <select value={count} onChange={(e) => setCount(Number(e.target.value))} className="ml-2 rounded border border-slate-300 px-2 py-1">
              {[10, 20, 30].map((n) => <option key={n}>{n}</option>)}
            </select>
          </label>
          <button
            onClick={() => setRunning(true)}
            disabled={scope === "exam" && open.length === 0}
            className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Start training
          </button>
        </div>
        {scope === "exam" ? (
          <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-1 font-semibold">Mistakes from your last exam</h2>
            {misses.isPending && <p className="text-slate-500">Loading…</p>}
            {misses.isError && <p role="alert" className="text-red-700">Couldn't load your exam mistakes.</p>}
            {misses.data && <ExamMissList data={misses.data} section={section} />}
          </section>
        ) : (
          <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-1 font-semibold">Your biggest weaknesses right now</h2>
            {weak.isPending && <p className="text-slate-500">Loading…</p>}
            {weak.isError && <p role="alert" className="text-red-700">Couldn't load weaknesses.</p>}
            <WeaknessList rows={rows} />
          </section>
        )}
      </div>
    </Shell>
  );
}

function ExamMissList({ data, section }: { data: ExamMisses; section: Section | null }) {
  if (data.exam_id === null)
    return (
      <p className="text-slate-600">
        You haven't finished a practice exam yet. <Link to="/exam" className="text-brand-700 underline">Take one</Link> and your mistakes will show up here.
      </p>
    );
  const keep = (m: { section: Section }) => section === null || m.section === section;
  const open = data.open.filter(keep);
  const cleared = data.cleared.filter(keep);
  const when = data.completed_at ? new Date(data.completed_at).toLocaleDateString() : "";
  return (
    <>
      <p className="mb-2 text-sm text-slate-500">Exam finished {when}.</p>
      {open.length === 0 && (
        <p className="text-slate-600">
          {data.open.length + data.cleared.length === 0 ? "No mistakes in that exam." : "Every mistake here is cleared."} Switch to All weaknesses, or take another{" "}
          <Link to="/exam" className="text-brand-700 underline">practice exam</Link>.
        </p>
      )}
      <ol className="divide-y divide-slate-100">
        {open.map((m, i) => (
          <li key={m.skill_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2">
            <span className="w-6 text-slate-500">{i + 1}.</span>
            <span className="flex-1">
              {m.name} <span className="text-xs text-slate-500">{m.section === "RW" ? "R&W" : "Math"}</span>
              <span className="block text-sm text-amber-700">Missed {m.missed} in the exam</span>
            </span>
            <span className="w-40 text-right text-sm tabular-nums text-slate-600">
              {m.streak}/{data.clear_streak} in a row
              <span className="mt-1 block h-1.5 rounded bg-slate-100" role="progressbar" aria-label={`${m.name} streak`} aria-valuemin={0} aria-valuemax={data.clear_streak} aria-valuenow={m.streak}>
                <span className="block h-full rounded bg-brand-600" style={{ width: `${(100 * m.streak) / data.clear_streak}%` }} />
              </span>
            </span>
          </li>
        ))}
      </ol>
      {cleared.length > 0 && (
        <p className="mt-3 text-sm text-emerald-700">
          Cleared: {cleared.map((m) => m.name).join(", ")}
        </p>
      )}
    </>
  );
}
