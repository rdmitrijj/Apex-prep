import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { nextQuestion, submitAnswer, type Feedback, type Question } from "../api/drill";
import { QuestionView } from "../components/QuestionView";
import { Shell } from "../components/Shell";

// Timing drill: answer, or mark and move on, so nothing is left blank when time runs out.
const COUNT = 10;
const LIMIT_MS = 12 * 60_000;
const NUDGE_MS = 90_000;

type Slot = { q: Question; answer: string | null; flagged: boolean; ms: number; fb?: Feedback };

const clock = (ms: number) => {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

function Results({ slots, onAgain }: { slots: Slot[]; onAgain: () => void }) {
  const blanks = slots.filter((s) => !s.answer).length;
  const right = slots.filter((s) => s.fb?.correct).length;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Triage results</h1>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><p className="text-sm text-slate-500">Correct</p><p className="text-4xl font-bold text-brand-700">{right}/{COUNT}</p></div>
        <div className={`rounded-xl p-5 shadow-sm ring-1 ${blanks ? "bg-red-50 ring-red-200" : "bg-emerald-50 ring-emerald-200"}`}>
          <p className="text-sm text-slate-600">Blanks left</p><p className="text-4xl font-bold">{blanks}</p>
          <p className="text-sm">{blanks ? "Every blank is a guaranteed zero. Guess before time runs out." : "No blanks. That's the habit."}</p>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><p className="text-sm text-slate-500">Over 90 s</p><p className="text-4xl font-bold">{slots.filter((s) => s.ms > NUDGE_MS).length}</p></div>
      </div>
      <ul className="divide-y divide-slate-100 rounded-xl bg-white px-5 shadow-sm ring-1 ring-slate-200">
        {slots.map((s, i) => (
          <li key={s.q.id} className="flex flex-wrap gap-x-3 py-2 text-sm">
            <span className="w-8 text-slate-500">#{i + 1}</span>
            <span className={`w-20 font-medium ${!s.answer ? "text-slate-500" : s.fb?.correct ? "text-emerald-700" : "text-red-700"}`}>{!s.answer ? "Blank" : s.fb?.correct ? "Correct" : "Incorrect"}</span>
            <span className="flex-1">{s.q.skill_name} <span className="capitalize text-slate-500">· {s.q.difficulty}</span></span>
            <span className={`tabular-nums ${s.ms > NUDGE_MS ? "text-red-700" : "text-slate-600"}`}>{Math.round(s.ms / 1000)} s</span>
          </li>
        ))}
      </ul>
      <div className="flex gap-4">
        <button onClick={onAgain} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">Another round</button>
        <Link to="/mistakes" className="self-center text-sm underline">Review misses in the Mistake Notebook</Link>
      </div>
    </div>
  );
}

function Run({ onDone }: { onDone: (slots: Slot[]) => void }) {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [now, setNow] = useState(() => performance.now());
  const [startAt, setStartAt] = useState(0);
  const [shownAt, setShownAt] = useState(0);
  const finishing = useRef(false);

  useEffect(() => {
    let live = true;
    (async () => {
      const got: Slot[] = [];
      for (let i = 0; i < COUNT; i++) {
        const q = await nextQuestion({ skill_ids: ["MATH"], difficulty: "mixed", exclude_ids: got.map((s) => s.q.id) });
        got.push({ q, answer: null, flagged: false, ms: 0 });
      }
      if (!live) return;
      setSlots(got);
      const t0 = performance.now();
      setStartAt(t0);
      setShownAt(t0);
    })().catch((e) => live && setErr(e instanceof ApiError ? e.message : "Couldn't load questions."));
    const t = setInterval(() => setNow(performance.now()), 500);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, []);

  const spent = (s: Slot[], i: number) => s.map((x, j) => (j === i ? { ...x, ms: x.ms + Math.max(0, now - shownAt) } : x));
  const go = (to: number, patch: Partial<Slot> = {}) => {
    setSlots((s) => spent(s, idx).map((x, j) => (j === idx ? { ...x, ...patch } : x)));
    setShownAt(now);
    setIdx(to);
  };
  const finish = async (s: Slot[]) => {
    if (finishing.current) return;
    finishing.current = true;
    const graded = await Promise.all(
      s.map(async (x) => (x.answer ? { ...x, fb: await submitAnswer({ question_id: x.q.id, answer: x.answer, time_ms: Math.round(x.ms), mode: "drill" }) } : x)),
    );
    onDone(graded);
  };

  const left = slots.length ? LIMIT_MS - (now - startAt) : LIMIT_MS;
  useEffect(() => {
    if (slots.length && left <= 0) void finish(spent(slots, idx));
  });

  if (err) return <p role="alert" className="text-red-700">{err}</p>;
  if (!slots.length) return <p className="text-slate-500">Loading 10 questions…</p>;
  const cur = slots[idx];
  const onThis = cur.ms + Math.max(0, now - shownAt);
  const nextIdx = (idx + 1) % COUNT;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-600">Question {idx + 1} of {COUNT} · {Math.round(onThis / 1000)} s on this one</p>
        <p role="timer" aria-label="Time remaining" className={`font-mono text-xl font-bold ${left < 2 * 60_000 ? "text-red-700" : ""}`}>{clock(left)}</p>
      </div>
      {onThis > NUDGE_MS && !cur.answer && (
        <p role="alert" className="rounded-md bg-amber-100 p-3 text-sm text-amber-950">90 seconds on this one. Pick your best guess, mark it, and move on.</p>
      )}
      <nav aria-label="Questions" className="flex flex-wrap gap-1">
        {slots.map((s, i) => (
          <button key={s.q.id} type="button" aria-current={i === idx} onClick={() => go(i)} className={`h-8 w-8 rounded text-sm ${i === idx ? "ring-2 ring-brand-600" : ""} ${s.answer ? "bg-brand-700 text-white" : "border border-dashed border-slate-400"}`}>
            {i + 1}{s.flagged ? "⚑" : ""}
          </button>
        ))}
      </nav>
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <QuestionView key={`${cur.q.id}-${cur.answer}`} q={cur.q} given={cur.answer} feedback={null} busy={false} error={null} submitLabel="Save and next" onSubmit={(a) => go(nextIdx, { answer: a })} />
      </div>
      <div className="flex flex-wrap justify-between gap-2">
        <button type="button" onClick={() => go(nextIdx, { flagged: true })} className="rounded-md border border-brand-700 px-4 py-2 text-brand-700">Mark and move on</button>
        <button type="button" onClick={() => void finish(spent(slots, idx))} className="rounded-md bg-slate-800 px-4 py-2 text-white">
          Finish ({slots.filter((s) => !s.answer).length} blank)
        </button>
      </div>
    </div>
  );
}

export function Triage() {
  const [phase, setPhase] = useState<"intro" | "run" | Slot[]>("intro");
  return (
    <Shell>
      {phase === "intro" && (
        <div className="max-w-2xl space-y-4">
          <h1 className="text-2xl font-bold">Triage drill</h1>
          <p className="text-slate-700">
            10 Math questions in 12 minutes: a little faster than the real pace (35 minutes for 22). After 90 seconds on a question you'll be nudged to guess, mark it, and
            move on. The goal is <strong>zero blanks</strong>: there's no penalty for a wrong answer, so a blank is the only sure way to lose a point.
          </p>
          <button onClick={() => setPhase("run")} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">Start (12:00)</button>
        </div>
      )}
      {phase === "run" && <Run onDone={setPhase} />}
      {Array.isArray(phase) && <Results slots={phase} onAgain={() => setPhase("run")} />}
    </Shell>
  );
}
