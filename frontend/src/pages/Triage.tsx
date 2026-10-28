import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { fmtClock, fmtDate, type ExamItem, type ItemState } from "../api/exam";
import {
  isFirstPass,
  missedVocabCsv,
  MODE_INFO,
  startTriage,
  submitTriage,
  timerColor,
  useTriageHistory,
  type Group,
  type ItemResult,
  type Results as ResultsData,
  type Started,
  type TriageMode,
} from "../api/triage";
import { Calculator } from "../components/Calculator";
import { MissReason } from "../components/MissReason";
import { QuestionView } from "../components/QuestionView";
import { ReferenceSheet } from "../components/ReferenceSheet";
import { Shell } from "../components/Shell";
import { Grid, QuestionPane } from "./ExamRunner";

const MODES = Object.keys(MODE_INFO) as TriageMode[];
const TIMER_TONE = { normal: "text-slate-600", amber: "text-amber-700", red: "font-semibold text-red-700" };
const pct = ([c, n]: [number, number]) => (n ? `${Math.round((100 * c) / n)}% (${c}/${n})` : "none");

function Picker({ busy, err, onStart }: { busy: boolean; err: string | null; onStart: (m: TriageMode) => void }) {
  const history = useTriageHistory();
  const recent = [...(history.data ?? [])].reverse().slice(0, 8);
  return (
    <div className="space-y-6">
      <div className="max-w-2xl space-y-2">
        <h1 className="text-2xl font-bold">Triage drills</h1>
        <p className="text-slate-700">
          Timed sets that train pace and skipping. Each question has a target time: the timer turns amber at the target and red 30 s past it. Answer fast on the
          first pass, mark the hard ones, come back if there's time, and leave <strong>zero blanks</strong>.
        </p>
      </div>
      {err && <p role="alert" className="text-red-700">{err}</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {MODES.map((m) => (
          <div key={m} className="flex flex-col gap-3 rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-lg font-semibold">{MODE_INFO[m].name}</h2>
            <p className="flex-1 text-sm text-slate-600">{MODE_INFO[m].blurb}</p>
            <button type="button" disabled={busy} onClick={() => onStart(m)} className="self-start rounded-md bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50">
              Start
            </button>
          </div>
        ))}
      </div>
      {recent.length > 0 && (
        <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-2 font-semibold">Recent sessions</h2>
          <ul className="divide-y divide-slate-100 text-sm">
            {recent.map((s) => (
              <li key={s.id} className="flex flex-wrap gap-x-4 py-2">
                <span className="w-28 text-slate-500">{fmtDate(s.created_at)}</span>
                <span className="w-40 font-medium">{MODE_INFO[s.mode]?.name ?? s.mode}</span>
                <span className="w-16 tabular-nums">{s.correct}/{s.total}</span>
                <span className={`w-20 ${s.blanks ? "text-red-700" : "text-slate-600"}`}>{s.blanks} blank</span>
                <span className="tabular-nums text-slate-600">{Math.round(s.avg_seconds)} s avg</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Run({ started, onDone }: { started: Started; onDone: (r: ResultsData) => void }) {
  const qs = started.questions;
  // Grid and QuestionPane take exam items; here an item's id is its question id.
  const items: ExamItem[] = qs.map((t, i) => ({ id: t.question.id, position: i + 1, question: t.question, answer: null, flagged: false, eliminated: [], time_ms: 0 }));
  const [states, setStates] = useState<Record<number, ItemState>>(() => Object.fromEntries(items.map((i) => [i.id, { answer: null, flagged: false, eliminated: [], time_ms: 0 }])));
  const [idx, setIdx] = useState(0);
  const [strike, setStrike] = useState(false);
  const [tool, setTool] = useState<"calc" | "ref" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [t0] = useState(() => performance.now());
  const [now, setNow] = useState(t0);
  const [enteredAt, setEnteredAt] = useState(t0);
  const firstLeft = useRef<Record<number, string | null>>({}); // answer when each question was first left
  const submitting = useRef(false);
  const expired = useRef(false);
  const [notesPrefix] = useState(() => `apex-annotations-triage-${Date.now()}`);

  const cur = items[idx];
  const left = started.limit_seconds * 1000 - (now - t0);
  const onThis = (states[cur.id].time_ms + now - enteredAt) / 1000;
  const target = qs[idx].target_seconds;

  // Adds the time since the current question was shown to its total.
  const banked = () => {
    const t = performance.now();
    const s = states[cur.id];
    const next = { ...states, [cur.id]: { ...s, time_ms: s.time_ms + t - enteredAt } };
    setEnteredAt(t);
    return next;
  };
  const go = (i: number) => {
    if (i === idx) return;
    if (!(cur.id in firstLeft.current)) firstLeft.current[cur.id] = states[cur.id].answer;
    setStates(banked());
    setIdx(i);
  };
  const finish = async () => {
    if (submitting.current) return;
    submitting.current = true;
    setErr(null);
    const final = banked();
    setStates(final);
    try {
      onDone(
        await submitTriage({
          mode: started.mode,
          elapsed_ms: Math.round(Math.min(performance.now() - t0, started.limit_seconds * 1000)),
          items: items.map(({ id }) => {
            const s = final[id];
            return { question_id: id, answer: s.answer || null, time_ms: Math.round(s.time_ms), flagged: s.flagged, first_pass: isFirstPass(s.answer || null, firstLeft.current[id]), eliminated: s.eliminated };
          }),
        }),
      );
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Couldn't submit. Check your connection and try again.");
      submitting.current = false;
    }
  };

  useEffect(() => {
    const t = window.setInterval(() => setNow(performance.now()), 250);
    return () => window.clearInterval(t);
  }, []);
  useEffect(() => {
    if (left > 0 || expired.current) return;
    expired.current = true; // auto-submit once; if that fails the Finish button still works
    void finish();
  });

  const blanks = items.filter((i) => !states[i.id].answer).length;
  const color = timerColor(onThis, target);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-semibold">{MODE_INFO[started.mode].name} · Question {idx + 1} of {items.length}</p>
          <p className={`text-sm tabular-nums ${TIMER_TONE[color]}`} aria-live={color === "normal" ? "off" : "polite"}>
            {Math.floor(onThis)} s on this one (target {target} s){color === "red" && ": guess, mark it, move on"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {started.mode === "math" && (
            <>
              <button type="button" aria-pressed={tool === "calc"} onClick={() => setTool((t) => (t === "calc" ? null : "calc"))} className="rounded px-2 py-1 text-sm hover:bg-slate-100">Calculator</button>
              <button type="button" aria-pressed={tool === "ref"} onClick={() => setTool((t) => (t === "ref" ? null : "ref"))} className="rounded px-2 py-1 text-sm hover:bg-slate-100">Reference</button>
            </>
          )}
          <p role="timer" aria-label="Time remaining" className={`font-mono text-xl font-bold ${left < 2 * 60_000 ? "text-red-700" : ""}`}>{fmtClock(left)}</p>
        </div>
      </div>
      {tool === "calc" && <Calculator onClose={() => setTool(null)} />}
      {tool === "ref" && <ReferenceSheet onClose={() => setTool(null)} />}
      <nav aria-label="Questions"><Grid items={items} states={states} current={idx} onPick={go} /></nav>
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <QuestionPane
          key={cur.id}
          item={cur}
          notesKey={`${notesPrefix}-${cur.id}`}
          n={idx + 1}
          state={states[cur.id]}
          strike={strike}
          onToggleStrike={() => setStrike((s) => !s)}
          onChange={(p) => setStates((s) => ({ ...s, [cur.id]: { ...s[cur.id], ...p } }))}
        />
      </div>
      {err && <p role="alert" className="text-red-700">{err}</p>}
      <div className="flex flex-wrap justify-between gap-2">
        <div className="flex gap-2">
          <button type="button" disabled={idx === 0} onClick={() => go(idx - 1)} className="rounded-md border border-brand-700 px-4 py-2 text-brand-700 disabled:opacity-40">Back</button>
          <button type="button" onClick={() => go((idx + 1) % items.length)} className="rounded-md bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600">Next</button>
        </div>
        <button type="button" onClick={() => void finish()} className="rounded-md bg-slate-800 px-4 py-2 text-white">Finish ({blanks} blank)</button>
      </div>
    </div>
  );
}

function GroupTable({ title, groups }: { title: string; groups: Group[] }) {
  return (
    <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h2 className="mb-2 font-semibold">{title}</h2>
      <table className="w-full text-sm">
        <thead className="text-left text-slate-500">
          <tr><th className="font-normal">Name</th><th className="font-normal">Correct</th><th className="text-right font-normal">Avg / target</th></tr>
        </thead>
        <tbody>
          {groups.map((g) => (
            <tr key={g.id} className="border-t border-slate-100">
              <td className="py-1.5 pr-2">{g.name}</td>
              <td className={`tabular-nums ${g.correct / g.total < 0.6 ? "text-red-700" : ""}`}>{g.correct}/{g.total}</td>
              <td className={`text-right tabular-nums ${g.avg_seconds > g.target_seconds ? "text-red-700" : "text-slate-600"}`}>{Math.round(g.avg_seconds)} / {Math.round(g.target_seconds)} s</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ItemRow({ item, n }: { item: ItemResult; n: number }) {
  const [open, setOpen] = useState(false);
  const status = item.answer === null ? "Blank" : item.correct ? "Correct" : "Incorrect";
  return (
    <li className="py-2">
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 text-left text-sm hover:bg-slate-50">
        <span className="w-8 text-slate-500">#{n}</span>
        <span className={`w-20 font-medium ${item.correct ? "text-emerald-700" : "text-red-700"}`}>{status}</span>
        <span className="flex-1">{item.question.skill_name}</span>
        <span className={`w-20 text-right tabular-nums ${item.seconds > item.target_seconds ? "text-red-700" : "text-slate-600"}`}>{Math.round(item.seconds)} / {item.target_seconds} s</span>
        <span className="w-6">{item.flagged ? "⚑" : ""}</span>
      </button>
      {open && (
        <div className="mt-3 space-y-3 rounded-lg p-4 ring-1 ring-slate-200">
          <QuestionView q={item.question} given={item.answer} busy={false} error={null} onSubmit={() => {}} feedback={{ correct: item.correct, answer: item.key, explanation: item.explanation, rationales: item.rationales }} />
          {item.vocab.length > 0 && (
            <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
              {item.vocab.map((v) => (
                <div key={v.word} className="contents">
                  <dt className="font-semibold">{v.word} <span className="font-normal text-slate-500">({v.pos})</span></dt>
                  <dd>{v.meaning_en} · {v.meaning_ru}</dd>
                </div>
              ))}
            </dl>
          )}
          {!item.correct && <MissReason responseId={item.response_id} initial={item.answer === null || item.time_sink ? "slow" : null} />}
        </div>
      )}
    </li>
  );
}

function download(csv: string, name: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

function Results({ r, onAgain, onPick }: { r: ResultsData; onAgain: () => void; onPick: () => void }) {
  const csv = missedVocabCsv(r.items);
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{MODE_INFO[r.mode].name} results</h1>
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><p className="text-sm text-slate-500">Correct</p><p className="text-4xl font-bold text-brand-700">{r.correct}/{r.total}</p></div>
        <div className={`rounded-xl p-5 shadow-sm ring-1 ${r.blanks ? "bg-red-50 ring-red-200" : "bg-emerald-50 ring-emerald-200"}`}>
          <p className="text-sm text-slate-600">Blanks</p><p className="text-4xl font-bold">{r.blanks}</p>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><p className="text-sm text-slate-500">Avg per question</p><p className="text-4xl font-bold">{Math.round(r.avg_seconds)} s</p></div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><p className="text-sm text-slate-500">Time used</p><p className="text-4xl font-bold">{fmtClock(r.elapsed_seconds * 1000)}</p><p className="text-sm text-slate-500">of {fmtClock(r.limit_seconds * 1000)}</p></div>
      </div>
      <p className="text-sm text-slate-700">
        First-pass accuracy {pct(r.first_pass)} · answers changed or given on a later visit {pct(r.second_pass)}
      </p>
      {r.recommendations.length > 0 && (
        <section className="rounded-xl bg-amber-50 p-5 ring-1 ring-amber-200">
          <h2 className="mb-2 font-semibold">What to fix next</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">{r.recommendations.map((t) => <li key={t}>{t}</li>)}</ul>
        </section>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <GroupTable title="By domain" groups={r.by_domain} />
        <GroupTable title="By skill" groups={r.by_skill} />
      </div>
      {r.time_sinks.length > 0 && (
        <p className="text-sm text-slate-700">
          <strong>Time sinks</strong> (over target and still wrong): {r.time_sinks.map((s) => `${s.name} ×${s.count}`).join(", ")}
        </p>
      )}
      <section className="rounded-xl bg-white px-5 py-3 shadow-sm ring-1 ring-slate-200">
        <h2 className="font-semibold">Questions</h2>
        <ul className="divide-y divide-slate-100">{r.items.map((it, i) => <ItemRow key={it.response_id} item={it} n={i + 1} />)}</ul>
      </section>
      <div className="flex flex-wrap items-center gap-4">
        <button type="button" onClick={onAgain} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">Same drill again</button>
        <button type="button" onClick={onPick} className="rounded-md border border-brand-700 px-5 py-2 text-brand-700">Pick another drill</button>
        {csv && <button type="button" onClick={() => download(csv, "missed_vocab.csv")} className="text-sm underline">Download missed words (Anki CSV)</button>}
        <Link to="/mistakes" className="text-sm underline">Mistake Notebook</Link>
      </div>
    </div>
  );
}

export function Triage() {
  const qc = useQueryClient();
  const [phase, setPhase] = useState<{ k: "pick" } | { k: "run"; started: Started } | { k: "done"; r: ResultsData }>({ k: "pick" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const start = (m: TriageMode) => {
    setBusy(true);
    setErr(null);
    startTriage(m)
      .then((started) => setPhase({ k: "run", started }))
      .catch((e) => {
        setErr(e instanceof ApiError ? e.message : "Couldn't load questions.");
        setPhase({ k: "pick" });
      })
      .finally(() => setBusy(false));
  };
  const done = (r: ResultsData) => {
    void qc.invalidateQueries({ queryKey: ["triage-history"] });
    setPhase({ k: "done", r });
    window.scrollTo(0, 0);
  };
  return (
    <Shell>
      {phase.k === "pick" && <Picker busy={busy} err={err} onStart={start} />}
      {phase.k === "run" && <Run started={phase.started} onDone={done} />}
      {phase.k === "done" && <Results r={phase.r} onAgain={() => start(phase.r.mode)} onPick={() => setPhase({ k: "pick" })} />}
    </Shell>
  );
}
