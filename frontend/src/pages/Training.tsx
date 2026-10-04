import { useState } from "react";
import { Link } from "react-router-dom";
import { trainingNext, useWeaknesses, type Section } from "../api/exam";
import { Shell } from "../components/Shell";
import { WeaknessList } from "../components/WeaknessList";
import { Session } from "./Drill";

export function Training() {
  const weak = useWeaknesses(40);
  const [section, setSection] = useState<Section | null>(null);
  const [count, setCount] = useState(20);
  const [running, setRunning] = useState(false);
  if (running)
    return (
      <Shell>
        <Session count={count} mode="training" fetchNext={(exclude) => trainingNext({ exclude_ids: exclude, section })} onDone={() => setRunning(false)} />
      </Shell>
    );
  const rows = (weak.data ?? []).filter((w) => section === null || w.section === section).slice(0, 10);
  return (
    <Shell>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Weakness Training</h1>
        <p className="text-slate-600">
          Questions come from the skills where you lose the most points: misses, slow answers, and skills you haven't practised lately, weighted by how often they appear on the test (Math counts 1.3× for your 700 target). Difficulty adapts so you get about two in three right.
          {weak.data?.every((w) => w.attempts === 0) && <> Take a <Link to="/exam" className="text-brand-700 underline">practice exam</Link> first so this knows where you stand.</>}
        </p>
        <div className="flex flex-wrap items-end gap-4">
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
          <button onClick={() => setRunning(true)} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">Start training</button>
        </div>
        <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-1 font-semibold">Your biggest weaknesses right now</h2>
          {weak.isPending && <p className="text-slate-500">Loading…</p>}
          {weak.isError && <p role="alert" className="text-red-700">Couldn't load weaknesses.</p>}
          <WeaknessList rows={rows} />
        </section>
      </div>
    </Shell>
  );
}
