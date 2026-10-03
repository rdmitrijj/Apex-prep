import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { nextQuestion, submitAnswer, useSkills, type Difficulty, type Feedback, type Question, type SkillNode } from "../api/drill";
import { QuestionView } from "../components/QuestionView";
import { Shell } from "../components/Shell";

type Setup = { skill_ids: string[]; difficulty: Difficulty | "mixed"; count: number };

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : e ? "Network error, try again." : null);

function accuracy(n: SkillNode) {
  if (!n.attempts) return <span className="text-slate-400">—</span>;
  const pct = Math.round((100 * n.correct) / n.attempts);
  const tone = pct >= 80 ? "text-emerald-700" : pct >= 60 ? "text-amber-700" : "text-red-700";
  return <span className={tone} title={`${n.correct} of ${n.attempts} correct`}>{pct}% <span className="text-slate-400">({n.attempts})</span></span>;
}

function Tree({ nodes, selected, toggle }: { nodes: SkillNode[]; selected: Set<string>; toggle: (id: string) => void }) {
  const kids = useMemo(() => {
    const m = new Map<string | null, SkillNode[]>();
    for (const n of nodes) m.set(n.parent_id, [...(m.get(n.parent_id) ?? []), n]);
    return m;
  }, [nodes]);
  const covered = (id: string) => [...selected].some((s) => id === s || id.startsWith(s + "."));

  const render = (n: SkillNode, depth: number) => {
    const inherited = covered(n.id) && !selected.has(n.id);
    const empty = !n.generated && n.available === 0;
    return (
      <li key={n.id}>
        <details open={depth < 2}>
          <summary className="flex cursor-pointer items-center gap-2 py-1 hover:bg-slate-50" style={{ paddingLeft: depth * 16 }}>
            <input
              type="checkbox"
              aria-label={n.name}
              checked={covered(n.id)}
              disabled={inherited || empty}
              onChange={() => toggle(n.id)}
              onClick={(e) => e.stopPropagation()}
            />
            <span className={`flex-1 ${n.level === "subskill" ? "text-sm" : "font-medium"} ${empty ? "text-slate-400" : ""}`}>{n.name}</span>
            <span className="w-16 text-right text-xs text-slate-500" title={n.generated ? "Unlimited generated questions" : "Stored questions"}>
              {n.generated ? "∞" : n.available}
            </span>
            <span className="w-24 text-right text-xs">{accuracy(n)}</span>
          </summary>
          {kids.get(n.id) && <ul>{kids.get(n.id)!.map((c) => render(c, depth + 1))}</ul>}
        </details>
      </li>
    );
  };
  return <ul className="divide-y divide-slate-100">{(kids.get(null) ?? []).map((n) => render(n, 0))}</ul>;
}

function Picker({ onStart }: { onStart: (s: Setup) => void }) {
  const skills = useSkills();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [difficulty, setDifficulty] = useState<Setup["difficulty"]>("mixed");
  const [count, setCount] = useState(10);
  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set([...prev].filter((s) => !s.startsWith(id + ".")));
      if (prev.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (skills.isPending) return <p>Loading skills…</p>;
  if (skills.isError) return <p role="alert" className="text-red-700">Couldn't load skills.</p>;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Topic Drill</h1>
      <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
        <div className="flex justify-end gap-4 px-1 pb-1 text-xs text-slate-500">
          <span className="w-16 text-right">Questions</span>
          <span className="w-24 text-right">Your accuracy</span>
        </div>
        <Tree nodes={skills.data} selected={selected} toggle={toggle} />
      </div>
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm">
          Difficulty
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as Setup["difficulty"])} className="ml-2 rounded border border-slate-300 px-2 py-1">
            <option value="mixed">Mixed</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
        <label className="text-sm">
          Questions
          <select value={count} onChange={(e) => setCount(Number(e.target.value))} className="ml-2 rounded border border-slate-300 px-2 py-1">
            {[5, 10, 20, 30].map((n) => <option key={n}>{n}</option>)}
          </select>
        </label>
        <button
          disabled={selected.size === 0}
          onClick={() => onStart({ skill_ids: [...selected], difficulty, count })}
          className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
        >
          Start drill
        </button>
      </div>
    </div>
  );
}

function Session({ setup, onDone }: { setup: Setup; onDone: () => void }) {
  const qc = useQueryClient();
  const [n, setN] = useState(0);
  const [q, setQ] = useState<Question | null>(null);
  const [fb, setFb] = useState<Feedback | null>(null);
  const [score, setScore] = useState(0);
  const seen = useRef<number[]>([]);
  const shownAt = useRef(0);

  const next = useMutation({
    mutationFn: () => nextQuestion({ skill_ids: setup.skill_ids, difficulty: setup.difficulty, exclude_ids: seen.current }),
    onSuccess: (question) => {
      seen.current.push(question.id);
      setQ(question);
      setFb(null);
      shownAt.current = performance.now();
    },
  });
  const answer = useMutation({
    mutationFn: (a: string) => submitAnswer({ question_id: q!.id, answer: a, time_ms: Math.round(performance.now() - shownAt.current) }),
    onSuccess: (f) => {
      setFb(f);
      if (f.correct) setScore((s) => s + 1);
      qc.invalidateQueries({ queryKey: ["skills"] });
    },
  });

  const started = useRef(false);
  useEffect(() => {
    if (started.current) return; // StrictMode runs effects twice in dev
    started.current = true;
    next.mutate();
  }, [next]);
  const finished = fb && n + 1 >= setup.count;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>
          Question {n + 1} of {setup.count}
          {q && <> · {q.skill_name} · <span className="capitalize">{q.difficulty}</span></>}
        </span>
        <span>Score {score}/{n + (fb ? 1 : 0)}</span>
      </div>
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        {next.isError && <p role="alert" className="text-red-700">{errMsg(next.error)}</p>}
        {next.isPending && <p className="text-slate-500">Loading question…</p>}
        {q && !next.isPending && <QuestionView key={q.id} q={q} feedback={fb} busy={answer.isPending} error={errMsg(answer.error)} onSubmit={(a) => answer.mutate(a)} />}
      </div>
      <div className="flex justify-between">
        <button onClick={onDone} className="text-sm text-slate-600 hover:underline">End drill</button>
        {fb && !finished && (
          <button
            autoFocus
            onClick={() => {
              setN((v) => v + 1);
              answer.reset();
              next.mutate();
            }}
            className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600"
          >
            Next question
          </button>
        )}
        {finished && (
          <div className="flex items-center gap-4">
            <span className="font-semibold">Done: {score} of {setup.count} correct.</span>
            <button autoFocus onClick={onDone} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">Back to skills</button>
          </div>
        )}
      </div>
    </div>
  );
}

export function Drill() {
  const [setup, setSetup] = useState<Setup | null>(null);
  return <Shell>{setup ? <Session setup={setup} onDone={() => setSetup(null)} /> : <Picker onStart={setSetup} />}</Shell>;
}
