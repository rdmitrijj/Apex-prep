import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Question } from "../api/drill";
import type { Section } from "../api/exam";
import { MissReason, REASONS } from "../components/MissReason";
import { QuestionView } from "../components/QuestionView";
import { Shell } from "../components/Shell";
import { Session } from "./Drill";

type Mistake = {
  response_id: number;
  mode: "exam" | "drill" | "training";
  created_at: string;
  question: Question;
  answer: string | null;
  key: string;
  time_ms: number;
  miss_reason: string | null;
  explanation: string[];
  rationales: Record<string, string>;
};
type Imported = {
  id: number;
  external_id: string;
  badge: string;
  section: Section;
  module: number;
  question_number: number;
  skill_name: string;
  domain_name: string;
  difficulty: string;
  result: "incorrect" | "omitted";
  my_answer: string | null;
  correct_answer: string;
  summary: string;
  lesson: string;
  where_to_review: string;
  miss_reason: string | null;
  twin_ids: number[];
  due: boolean;
  due_at: string;
  retired: boolean;
};
type Filters = { section: Section | ""; mode: string; reason: string };

const MODE_NAME: Record<Mistake["mode"], string> = { exam: "Exam", drill: "Drill", training: "Training" };
const REASON_NAME = Object.fromEntries(REASONS) as Record<string, string>;

function Row({ m }: { m: Mistake }) {
  const [open, setOpen] = useState(false);
  const q = m.question;
  const retry = `/drill?skills=${encodeURIComponent(q.skill_id)}&difficulty=${q.difficulty}&count=3`;
  return (
    <li className="py-2">
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex w-full flex-wrap items-center gap-x-3 text-left text-sm hover:bg-slate-50">
        <span className="w-24 text-slate-500">{new Date(m.created_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
        <span className="w-16 text-slate-600">{MODE_NAME[m.mode]}</span>
        <span className="flex-1">{q.skill_name} <span className="capitalize text-slate-500">· {q.difficulty}</span></span>
        <span className="text-xs text-amber-800">{m.miss_reason ? REASON_NAME[m.miss_reason] : ""}</span>
      </button>
      {open && (
        <div className="mt-3 space-y-3 rounded-lg p-4 ring-1 ring-slate-200">
          <p className="text-xs text-slate-500">
            {m.answer ? `You answered ${m.answer}` : "Left blank"} · {Math.round(m.time_ms / 1000)} s
          </p>
          <QuestionView q={q} given={m.answer} busy={false} error={null} onSubmit={() => {}} feedback={{ correct: false, answer: m.key, explanation: m.explanation, rationales: m.rationales }} />
          <MissReason responseId={m.response_id} initial={m.miss_reason} />
          <Link to={retry} className="inline-block rounded-md bg-brand-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-600">Retry 3 similar questions</Link>
        </div>
      )}
    </li>
  );
}

function status(m: Imported) {
  if (m.retired) return <span className="text-xs text-emerald-700">Retired</span>;
  if (m.due) return <span className="rounded-full bg-amber-100 px-2 text-xs font-medium text-amber-900">Due today</span>;
  return <span className="text-xs text-slate-500">Next review {new Date(m.due_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>;
}

function ImportedRow({ m }: { m: Imported }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [practice, setPractice] = useState(false);
  const twins = (exclude: number[]) =>
    api<Question[]>(`/imported-mistakes/${m.id}/twins`).then((all) => ({ question: all.find((q) => !exclude.includes(q.id)) ?? all[0] }));
  return (
    <li className="py-2">
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex w-full flex-wrap items-center gap-x-3 text-left text-sm hover:bg-slate-50">
        <span className="rounded bg-brand-50 px-2 text-xs font-medium text-brand-900 ring-1 ring-brand-100">{m.badge}</span>
        <span className="w-16 text-slate-600">M{m.module} Q{m.question_number}</span>
        <span className="flex-1">{m.skill_name} <span className="text-slate-500">· {m.result === "omitted" ? "left blank" : "incorrect"}</span></span>
        {status(m)}
      </button>
      {open && (
        <div className="mt-3 space-y-3 rounded-lg p-4 text-sm ring-1 ring-slate-200">
          <p className="text-slate-500">{m.domain_name} · {m.skill_name} · <span className="capitalize">{m.difficulty}</span></p>
          <p>{m.summary}</p>
          <p>
            <span className="text-slate-600">You: </span><span className="font-medium">{m.my_answer ?? "left blank"}</span>
            <span className="text-slate-600"> → Correct: </span><span className="font-medium text-emerald-800">{m.correct_answer}</span>
          </p>
          <p className="rounded-md bg-amber-50 p-3 text-amber-950"><span className="font-semibold">Lesson: </span>{m.lesson}</p>
          <p className="text-slate-600">Review in Bluebook: {m.where_to_review.replace(/^Bluebook → /, "")}</p>
          <MissReason responseId={m.id} initial={m.miss_reason} path={`/imported-mistakes/${m.id}/reason`} />
          {practice ? (
            <Session
              count={m.twin_ids.length}
              mode="drill"
              fetchNext={twins}
              onDone={() => {
                setPractice(false);
                qc.invalidateQueries({ queryKey: ["imported"] });
              }}
            />
          ) : (
            <button type="button" disabled={m.twin_ids.length === 0} onClick={() => setPractice(true)} className="rounded-md bg-brand-700 px-4 py-1.5 font-medium text-white hover:bg-brand-600 disabled:opacity-50">
              Practice twins ({m.twin_ids.length})
            </button>
          )}
        </div>
      )}
    </li>
  );
}

export function Mistakes() {
  const [f, setF] = useState<Filters>({ section: "", mode: "", reason: "" });
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v));
  const list = useQuery({ queryKey: ["mistakes", f], queryFn: () => api<Mistake[]>(`/mistakes?limit=200&${qs}`) });
  const imported = useQuery({ queryKey: ["imported"], queryFn: () => api<Imported[]>("/imported-mistakes") });
  const shown = imported.data?.filter((m) => (!f.section || m.section === f.section) && (!f.reason || m.miss_reason === f.reason || (f.reason === "untagged" && !m.miss_reason)));
  const [showRetired, setShowRetired] = useState(false);
  const select = "ml-2 rounded border border-slate-300 px-2 py-1";
  const reasons = list.data?.reduce<Record<string, number>>((acc, m) => ({ ...acc, [m.miss_reason ?? "untagged"]: (acc[m.miss_reason ?? "untagged"] ?? 0) + 1 }), {});
  return (
    <Shell>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Mistake Notebook</h1>
        <p className="text-slate-600">Every question you've missed, newest first. Tag why you missed it, reread the solution, then retry fresh questions on the same skill.</p>
        <div className="flex flex-wrap gap-4 text-sm">
          <label>Section
            <select value={f.section} onChange={(e) => setF({ ...f, section: e.target.value as Filters["section"] })} className={select}>
              <option value="">Both</option>
              <option value="MATH">Math</option>
              <option value="RW">Reading and Writing</option>
            </select>
          </label>
          <label>From
            <select value={f.mode} onChange={(e) => setF({ ...f, mode: e.target.value })} className={select}>
              <option value="">Everywhere</option>
              <option value="exam">Exams</option>
              <option value="drill">Topic drills</option>
              <option value="training">Weakness training</option>
            </select>
          </label>
          <label>Reason
            <select value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} className={select}>
              <option value="">Any</option>
              <option value="untagged">Not tagged yet</option>
              {REASONS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
          </label>
        </div>
        {reasons && !f.reason && list.data!.length > 0 && (
          <p className="text-sm text-slate-600">
            {REASONS.filter(([id]) => reasons[id]).map(([id, label]) => `${label}: ${reasons[id]}`).join(" · ")}
            {reasons.untagged ? `${REASONS.some(([id]) => reasons[id]) ? " · " : ""}Not tagged: ${reasons.untagged}` : ""}
          </p>
        )}
        {shown && shown.length > 0 && !f.mode && (
          <section aria-labelledby="official-h" className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="official-h" className="text-lg font-semibold">Official practice tests</h2>
              <p className="text-sm text-slate-600">
                {shown.filter((m) => m.due).length} due for review · {shown.filter((m) => m.retired).length} retired ·{" "}
                <button type="button" onClick={() => setShowRetired((v) => !v)} className="underline">{showRetired ? "hide" : "show"} retired</button>
              </p>
            </div>
            <p className="mt-1 text-sm text-slate-600">Practise the 3 twin questions; a mistake retires once you get all of them right on two separate days.</p>
            <ul className="mt-2 divide-y divide-slate-100">{shown.filter((m) => showRetired || !m.retired).map((m) => <ImportedRow key={m.id} m={m} />)}</ul>
          </section>
        )}
        <section className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          {list.isPending && <p className="text-slate-500">Loading…</p>}
          {list.isError && <p role="alert" className="text-red-700">Couldn't load your mistakes.</p>}
          {list.data?.length === 0 && <p className="text-slate-500">No mistakes here. Nice.</p>}
          <ul className="divide-y divide-slate-100">{list.data?.map((m) => <Row key={m.response_id} m={m} />)}</ul>
        </section>
      </div>
    </Shell>
  );
}
