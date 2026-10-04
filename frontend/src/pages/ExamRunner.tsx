import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { validSpr } from "../api/drill";
import {
  fmtClock,
  MODULE_MINUTES,
  MODULE_QUESTIONS,
  saveItem,
  SECTION_NAME,
  startModule,
  submitModule,
  useExamState,
  type ExamItem,
  type ExamState,
  type ItemState,
} from "../api/exam";
import { Calculator } from "../components/Calculator";
import { Figure } from "../components/Figure";
import { Logo } from "../components/Logo";
import { MathText } from "../components/MathText";
import { Passage } from "../components/QuestionView";
import { ReferenceSheet } from "../components/ReferenceSheet";

const LETTERS = ["A", "B", "C", "D"];
const FIVE_MIN = 5 * 60_000;

function sprTex(entry: string) {
  const neg = entry.startsWith("-");
  const [num, den] = (neg ? entry.slice(1) : entry).split("/");
  return `$${neg ? "-" : ""}${den !== undefined ? `\\frac{${num}}{${den}}` : num}$`;
}

type SaveStatus = "saved" | "saving" | "offline";

// Queues the latest state per item and retries until the server has it (survives brief network loss).
export class Autosave {
  private pending = new Map<number, ItemState>();
  private chain = Promise.resolve();
  private retry: number | undefined;
  constructor(
    private examId: number,
    private onStatus: (s: SaveStatus) => void,
    private onClosed: () => void,
  ) {}

  save(itemId: number, body: ItemState) {
    this.pending.set(itemId, body);
    return this.flush();
  }

  flush() {
    return (this.chain = this.chain.then(() => this.drain()));
  }

  unsaved() {
    return this.pending.size;
  }

  dispose() {
    window.clearTimeout(this.retry);
  }

  private async drain() {
    while (this.pending.size) {
      const [itemId, body] = this.pending.entries().next().value!;
      this.onStatus("saving");
      try {
        await saveItem(this.examId, itemId, body);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          this.pending.clear();
          this.onStatus("saved");
          this.onClosed(); // the module closed on the server (time ran out)
          return;
        }
        if (!(e instanceof ApiError) || e.status >= 500) {
          this.onStatus("offline");
          window.clearTimeout(this.retry);
          this.retry = window.setTimeout(() => void this.flush(), 3000);
          return;
        }
        // Other 4xx: the entry itself is bad; drop it rather than retrying forever.
      }
      if (this.pending.get(itemId) === body) this.pending.delete(itemId);
    }
    this.onStatus("saved");
  }
}

function ModuleIntro({ exam, onState }: { exam: ExamState; onState: (s: ExamState) => void }) {
  const m = exam.module!;
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [breakLeft, setBreakLeft] = useState(exam.break_remaining_ms);
  const [breakEnd] = useState(() => performance.now() + (exam.break_remaining_ms ?? 0));
  useEffect(() => {
    if (exam.break_remaining_ms == null) return;
    const t = window.setInterval(() => setBreakLeft(Math.max(0, breakEnd - performance.now())), 500);
    return () => window.clearInterval(t);
  }, [exam.break_remaining_ms, breakEnd]);

  const start = () => {
    setBusy(true);
    startModule(exam.id).then(onState, (e) => {
      setErr(e instanceof ApiError ? e.message : "Network error, try again.");
      setBusy(false);
    });
  };
  const onBreak = breakLeft != null;
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-lg space-y-4 rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-slate-200">
        {onBreak ? (
          <>
            <p className="text-sm uppercase tracking-wide text-slate-500">Break</p>
            <p className="font-mono text-5xl font-bold text-brand-700" role="timer">{fmtClock(breakLeft)}</p>
            <p className="text-slate-600">
              Stretch, drink some water. Math starts when you're ready{breakLeft === 0 ? "; your break time is up" : ""}.
            </p>
          </>
        ) : (
          <>
            <p className="text-sm uppercase tracking-wide text-slate-500">Module {m.index} of {exam.total_modules}</p>
            <h1 className="text-2xl font-bold">{SECTION_NAME[m.section]}: Module {m.stage}</h1>
            <p className="text-slate-600">
              {MODULE_QUESTIONS[m.section]} questions · {MODULE_MINUTES[m.section]} minutes.
              {m.section === "MATH" && " Calculator and reference sheet are in the toolbar."} Once you submit or time runs out, you can't come back to this module.
            </p>
          </>
        )}
        {err && <p role="alert" className="text-red-700">{err}</p>}
        <button onClick={start} disabled={busy} className="rounded-md bg-brand-700 px-6 py-2.5 font-medium text-white hover:bg-brand-600 disabled:opacity-50">
          {onBreak ? "Resume testing" : `Start module ${m.index}`}
        </button>
        <p><Link to="/exam" className="text-sm text-slate-500 hover:underline">Leave (your progress is saved)</Link></p>
      </div>
    </div>
  );
}

function Grid({ items, states, current, onPick }: { items: ExamItem[]; states: Record<number, ItemState>; current: number; onPick: (i: number) => void }) {
  return (
    <div className="grid grid-cols-8 gap-2 sm:grid-cols-10">
      {items.map((it, i) => {
        const s = states[it.id];
        const answered = s.answer !== null && s.answer !== "";
        return (
          <button
            key={it.id}
            type="button"
            onClick={() => onPick(i)}
            aria-label={`Question ${i + 1}${answered ? ", answered" : ", unanswered"}${s.flagged ? ", marked for review" : ""}`}
            className={`relative h-9 rounded border-2 text-sm font-semibold ${answered ? "border-brand-700 bg-brand-700 text-white" : "border-dashed border-slate-400 text-slate-700"} ${i === current ? "ring-2 ring-accent ring-offset-1" : ""}`}
          >
            {i + 1}
            {s.flagged && <span className="absolute -right-1 -top-1.5 text-xs text-red-600" aria-hidden>⚑</span>}
          </button>
        );
      })}
    </div>
  );
}

function QuestionPane({
  item,
  n,
  state,
  strike,
  onChange,
  onToggleStrike,
}: {
  item: ExamItem;
  n: number;
  state: ItemState;
  strike: boolean;
  onChange: (patch: Partial<ItemState>) => void;
  onToggleStrike: () => void;
}) {
  const q = item.question;
  const isRW = q.skill_id.startsWith("RW");
  const [entry, setEntry] = useState(state.answer ?? "");
  const header = (
    <div className="flex items-center gap-3 border-b-2 border-dashed border-slate-300 bg-slate-100 px-2 py-1.5">
      <span className="flex h-7 w-7 items-center justify-center bg-slate-900 text-sm font-bold text-white">{n}</span>
      <button type="button" aria-pressed={state.flagged} onClick={() => onChange({ flagged: !state.flagged })} className={`text-sm ${state.flagged ? "font-semibold text-red-700" : "text-slate-700"}`}>
        {state.flagged ? "⚑ Marked for review" : "⚐ Mark for review"}
      </button>
      {q.format === "mc" && (
        <button type="button" aria-pressed={strike} onClick={onToggleStrike} title="Option eliminator" className={`ml-auto rounded border px-2 text-sm line-through ${strike ? "border-brand-700 bg-brand-700 text-white" : "border-slate-400"}`}>
          ABC
        </button>
      )}
    </div>
  );
  const choices = q.format === "mc" ? (
    <div role="radiogroup" aria-label="Answer choices" className="space-y-2">
      {q.choices!.map((c, i) => {
        const L = LETTERS[i];
        const out = state.eliminated.includes(L);
        const picked = state.answer === L;
        return (
          <div key={L} className="flex items-center gap-2">
            <button
              type="button"
              role="radio"
              aria-checked={picked}
              onClick={() => onChange({ answer: L, eliminated: state.eliminated.filter((e) => e !== L) })}
              className={`flex flex-1 items-start gap-3 rounded-lg border-2 px-3 py-2 text-left ${picked ? "border-brand-600 bg-brand-50 ring-2 ring-brand-500" : "border-slate-300 hover:border-brand-500"} ${out ? "opacity-50" : ""}`}
            >
              <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-sm font-semibold ${picked ? "border-brand-700 bg-brand-700 text-white" : "border-current"}`}>{L}</span>
              <span className={out ? "line-through" : ""}><MathText text={c} /></span>
            </button>
            {strike && (
              <button
                type="button"
                aria-label={out ? `Undo eliminate ${L}` : `Eliminate ${L}`}
                onClick={() =>
                  onChange(
                    out
                      ? { eliminated: state.eliminated.filter((e) => e !== L) }
                      : { eliminated: [...state.eliminated, L], answer: picked ? null : state.answer },
                  )
                }
                className="w-14 text-xs text-slate-600 underline"
              >
                {out ? "Undo" : <span className="line-through">{L}</span>}
              </button>
            )}
          </div>
        );
      })}
    </div>
  ) : (
    <label className="block">
      <span className="text-sm font-medium">Your answer</span>
      <input
        value={entry}
        onChange={(e) => {
          const v = e.target.value.replace(/[^0-9./-]/g, "");
          setEntry(v);
          onChange({ answer: validSpr(v) ? v : null });
        }}
        maxLength={6}
        inputMode="decimal"
        aria-label="Your answer"
        className="mt-1 block w-40 rounded-md border border-slate-300 px-3 py-2 font-mono text-lg"
      />
      <span className="mt-1 block text-sm">
        Answer preview: {entry && validSpr(entry) ? <MathText text={sprTex(entry)} /> : <span className="text-slate-400">{entry ? "not a valid entry yet" : "—"}</span>}
      </span>
      <span className="text-xs text-slate-500">Fraction (7/2) or decimal (3.5). Up to 5 characters, 6 if negative.</span>
    </label>
  );
  const question = (
    <div className="space-y-4">
      {header}
      {!isRW && q.figure && <Figure spec={q.figure} />}
      <p className="leading-relaxed"><MathText text={q.stem} /></p>
      {choices}
    </div>
  );
  if (!isRW) return <div className="mx-auto max-w-3xl">{question}</div>;
  return (
    <div className="grid gap-6 md:grid-cols-2 md:divide-x-4 md:divide-slate-200">
      <div className="max-h-[calc(100vh-10rem)] overflow-auto pr-2"><Passage q={q} /></div>
      <div className="md:pl-6">{question}</div>
    </div>
  );
}

function Module({ exam, onState, refetch }: { exam: ExamState; onState: (s: ExamState) => void; refetch: () => void }) {
  const m = exam.module!;
  const items = m.items;
  const [idx, setIdx] = useState(0);
  const [reviewing, setReviewing] = useState(false);
  const [states, setStates] = useState<Record<number, ItemState>>(() =>
    Object.fromEntries(items.map((i) => [i.id, { answer: i.answer, flagged: i.flagged, eliminated: i.eliminated, time_ms: i.time_ms }])),
  );
  const [strike, setStrike] = useState(false);
  const [tool, setTool] = useState<"calc" | "ref" | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const [hideTimer, setHideTimer] = useState(false);
  const [warned, setWarned] = useState((m.remaining_ms ?? 0) <= FIVE_MIN);
  const [banner, setBanner] = useState(false);
  const [submitErr, setSubmitErr] = useState<string | null>(null);
  const [deadline] = useState(() => performance.now() + (m.remaining_ms ?? 0));
  const [left, setLeft] = useState(m.remaining_ms ?? 0);
  const enteredAt = useRef(0);
  const submitting = useRef(false);
  const expired = useRef(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [saver] = useState(() => new Autosave(exam.id, setSaveStatus, refetch));
  useEffect(() => {
    enteredAt.current = performance.now();
    return () => saver.dispose();
  }, [saver]);

  const current = items[idx];
  const withTime = (id: number, patch: Partial<ItemState> = {}): ItemState => {
    const extra = id === current.id && !reviewing ? performance.now() - enteredAt.current : 0;
    if (id === current.id) enteredAt.current = performance.now();
    return { ...states[id], ...patch, time_ms: Math.round(states[id].time_ms + extra) };
  };
  const update = (id: number, patch: Partial<ItemState> = {}) => {
    const next = withTime(id, patch);
    setStates((p) => ({ ...p, [id]: next }));
    void saver.save(id, next);
  };
  const go = (i: number | "review") => {
    if (!reviewing) update(current.id); // bank the time spent on the question being left
    enteredAt.current = performance.now();
    setNavOpen(false);
    if (i === "review") setReviewing(true);
    else {
      setReviewing(false);
      setIdx(i);
    }
  };

  const submit = useCallback(
    async (force: boolean) => {
      if (submitting.current) return;
      submitting.current = true;
      setSubmitErr(null);
      await saver.flush();
      if (saver.unsaved() && !force) {
        setSubmitErr("Some answers haven't reached the server yet. Check your connection and try again.");
        submitting.current = false;
        return;
      }
      try {
        onState(await submitModule(exam.id));
      } catch {
        setSubmitErr("Couldn't submit. Check your connection and try again.");
        submitting.current = false;
      }
    },
    [exam.id, onState, saver],
  );

  useEffect(() => {
    const t = window.setInterval(() => {
      const l = deadline - performance.now();
      setLeft(l);
      if (l <= FIVE_MIN && !warned) {
        setWarned(true);
        setBanner(true);
      }
      if (l <= 0 && !expired.current) {
        expired.current = true; // auto-submit once; if that fails the Submit button still works
        setReviewing(true);
        void submit(true);
      }
    }, 250);
    return () => window.clearInterval(t);
  }, [submit, warned, deadline]);

  // Keyboard: A–D choose, M marks for review, arrows move between questions.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (reviewing || e.ctrlKey || e.metaKey || e.altKey || t.closest("input, textarea, [contenteditable]")) return;
      const k = e.key.toUpperCase();
      if (current.question.format === "mc" && LETTERS.includes(k)) update(current.id, { answer: k, eliminated: states[current.id].eliminated.filter((x) => x !== k) });
      else if (k === "M") update(current.id, { flagged: !states[current.id].flagged });
      else if (e.key === "ArrowRight") go(idx + 1 < items.length ? idx + 1 : "review");
      else if (e.key === "ArrowLeft" && idx > 0) go(idx - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const unanswered = items.filter((i) => !states[i.id].answer).length;
  const flagged = items.filter((i) => states[i.id].flagged).length;
  const showTimer = !hideTimer || left <= FIVE_MIN;
  const last = m.index === exam.total_modules;

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="grid grid-cols-3 items-center border-b-2 border-dashed border-slate-300 px-4 py-2">
        <div>
          <p className="text-sm font-semibold">Section {exam.sections.indexOf(m.section) + 1}, Module {m.stage}: {SECTION_NAME[m.section]}</p>
          <p className="text-xs text-slate-500" aria-live="polite">
            {saveStatus === "offline" ? <span className="text-red-700">Offline: answers will save when you reconnect</span> : saveStatus === "saving" ? "Saving…" : "All answers saved"}
          </p>
        </div>
        <div className="text-center">
          {showTimer && <p role="timer" aria-label="Time remaining" className={`font-mono text-xl font-bold ${left <= FIVE_MIN ? "text-red-700" : ""}`}>{fmtClock(left)}</p>}
          {left > FIVE_MIN && (
            <button type="button" onClick={() => setHideTimer((h) => !h)} className="rounded-full border border-slate-400 px-3 text-xs">
              {hideTimer ? "Show" : "Hide"}
            </button>
          )}
        </div>
        <div className="flex justify-end gap-2 text-sm">
          {m.section === "MATH" && (
            <>
              <button type="button" aria-pressed={tool === "calc"} onClick={() => setTool((t) => (t === "calc" ? null : "calc"))} className="rounded px-2 py-1 hover:bg-slate-100">Calculator</button>
              <button type="button" aria-pressed={tool === "ref"} onClick={() => setTool((t) => (t === "ref" ? null : "ref"))} className="rounded px-2 py-1 hover:bg-slate-100">Reference</button>
            </>
          )}
        </div>
      </header>
      {banner && (
        <div role="alert" className="flex items-center justify-center gap-4 bg-amber-100 py-2 text-sm">
          5 minutes remaining in this module.
          <button type="button" onClick={() => setBanner(false)} className="underline">Dismiss</button>
        </div>
      )}
      {tool === "calc" && <Calculator onClose={() => setTool(null)} />}
      {tool === "ref" && <ReferenceSheet onClose={() => setTool(null)} />}

      <main className="flex-1 overflow-auto p-6">
        {reviewing ? (
          <div className="mx-auto max-w-2xl space-y-6 text-center">
            <h1 className="text-2xl font-bold">Check your work</h1>
            <p className="text-slate-600">
              Click a question to go back to it. {unanswered > 0 && <strong className="text-red-700">{unanswered} unanswered. There's no penalty for guessing. </strong>}
              {flagged > 0 && `${flagged} marked for review.`}
            </p>
            <div className="rounded-xl p-6 ring-1 ring-slate-200"><Grid items={items} states={states} current={-1} onPick={go} /></div>
            {submitErr && <p role="alert" className="text-red-700">{submitErr}</p>}
          </div>
        ) : (
          <QuestionPane key={current.id} item={current} n={idx + 1} state={states[current.id]} strike={strike} onToggleStrike={() => setStrike((s) => !s)} onChange={(p) => update(current.id, p)} />
        )}
      </main>

      <footer className="relative flex items-center justify-between border-t-2 border-dashed border-slate-300 px-4 py-2">
        <Link to="/" className="flex items-center gap-2 text-sm font-semibold text-brand-900" onClick={() => void saver.flush()}>
          <Logo className="h-6 w-6" /> <span className="hidden sm:inline">Apex Prep</span>
        </Link>
        {!reviewing && (
          <button type="button" aria-expanded={navOpen} onClick={() => setNavOpen((o) => !o)} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white">
            Question {idx + 1} of {items.length} ▾
          </button>
        )}
        {navOpen && (
          <div className="absolute bottom-14 left-1/2 z-20 w-[min(36rem,95vw)] -translate-x-1/2 space-y-3 rounded-xl bg-white p-4 shadow-2xl ring-1 ring-slate-300">
            <p className="text-center text-sm font-semibold">{SECTION_NAME[m.section]} · Module {m.stage}</p>
            <Grid items={items} states={states} current={idx} onPick={go} />
            <button type="button" onClick={() => go("review")} className="mx-auto block rounded-full border border-brand-700 px-4 py-1 text-sm text-brand-700">Go to review page</button>
          </div>
        )}
        <div className="flex gap-2">
          {(reviewing || idx > 0) && (
            <button type="button" onClick={() => go(reviewing ? items.length - 1 : idx - 1)} className="rounded-full bg-brand-700 px-5 py-1.5 font-medium text-white hover:bg-brand-600">Back</button>
          )}
          {reviewing ? (
            <button type="button" onClick={() => void submit(false)} className="rounded-full bg-brand-700 px-5 py-1.5 font-medium text-white hover:bg-brand-600">
              {last ? "Submit and finish" : "Submit module"}
            </button>
          ) : (
            <button type="button" onClick={() => go(idx + 1 < items.length ? idx + 1 : "review")} className="rounded-full bg-brand-700 px-5 py-1.5 font-medium text-white hover:bg-brand-600">Next</button>
          )}
        </div>
      </footer>
    </div>
  );
}

export function ExamRunner() {
  const id = Number(useParams().id);
  const qc = useQueryClient();
  const st = useExamState(id);
  const onState = useCallback(
    (s: ExamState) => {
      qc.setQueryData(["exam", id], s);
      qc.invalidateQueries({ queryKey: ["exams"] });
    },
    [qc, id],
  );
  const refetch = useCallback(() => void qc.invalidateQueries({ queryKey: ["exam", id] }), [qc, id]);

  if (st.isPending) return <p className="p-6 text-slate-500">Loading exam…</p>;
  if (st.isError) return <p role="alert" className="p-6 text-red-700">{st.error instanceof ApiError ? st.error.message : "Couldn't load the exam."} <Link to="/exam" className="underline">Back</Link></p>;
  const s = st.data;
  if (s.status === "completed") return <Navigate to={`/exam/${id}/results`} replace />;
  if (s.status === "abandoned" || !s.module)
    return <p className="p-6">This exam was replaced by a newer one. <Link to="/exam" className="underline">Back to exams</Link></p>;
  if (!s.module.started) return <ModuleIntro key={s.module.id} exam={s} onState={onState} />;
  return <Module key={s.module.id} exam={s} onState={onState} refetch={refetch} />;
}
