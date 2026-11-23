import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Question } from "../api/drill";
import { useOfficialScores } from "../api/exam";
import { Shell } from "../components/Shell";
import { Session } from "./Drill";

const card = "rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200";
const btn = "rounded-md border border-brand-700 px-3 py-1 text-sm text-brand-700 hover:bg-brand-50";
type Part = "rw" | "math" | "all";
const PARTS: Record<Part, string> = { rw: "R&W (25)", math: "Math (10)", all: "All 35" };
const TESTS = [
  { name: "PT4", date: "2026-10-01" },
  { name: "PT5", date: "2026-11-11" },
  { name: "PT6", date: "2026-11-22" },
];

function Scores() {
  const scores = useOfficialScores().data?.scores ?? [];
  const cell = "px-3 py-1 text-right tabular-nums";
  return (
    <table className="text-sm">
      <thead>
        <tr className="text-slate-600"><th className="px-3 py-1 text-left font-normal">Test</th><th className={`${cell} font-normal`}>Total</th><th className={`${cell} font-normal`}>R&W</th><th className={`${cell} font-normal`}>Math</th></tr>
      </thead>
      <tbody>
        {TESTS.map((t) => {
          const s = scores.find((x) => x.taken_on === t.date && x.kind === "practice");
          return (
            <tr key={t.name} className={t.name === "PT6" ? "font-semibold" : ""}>
              <td className="px-3 py-1">{t.name} <span className="font-normal text-slate-500">({new Date(t.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })})</span></td>
              {s ? (
                <><td className={cell}>{s.rw + s.math}</td><td className={cell}>{s.rw}</td><td className={cell}>{s.math}</td></>
              ) : (
                <td colSpan={3} className="px-3 py-1 text-right font-normal"><Link to="/exam#official" className="underline">Add the score</Link></td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Overview() {
  return (
    <div className="max-w-3xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">PT6 Replay</h1>
        <p className="text-slate-700">
          One new twin for every PT6 question you missed, skipped, or guessed, in the order of the test. Same skill, same trap, same answer letter; new topic and new numbers.
        </p>
      </div>
      <section className={`${card} flex flex-wrap gap-x-10 gap-y-4`}>
        <Scores />
        <div className="max-w-sm space-y-1 text-sm text-slate-700">
          <p><strong>PT6 errors:</strong> R&W 22 (M1: 6, M2: 16), Math 10 (M1: 3, M2: 7).</p>
          <p><strong>6 of 32 were blanks</strong> at the end of a module. Pacing is problem #1: guess every blank.</p>
          <p>Weakest: words with academic meanings, evidence with the right baseline, geometry facts, and "answer the question asked".</p>
        </div>
      </section>
      <section className={card}>
        <h2 className="font-semibold">Practice</h2>
        <p className="mb-3 text-sm text-slate-600">Instant feedback after each answer. If you fall into the same trap as in PT6, you'll see it.</p>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(PARTS) as Part[]).map((p) => <Link key={p} to={`/pt6?practice=${p}`} className={btn}>{PARTS[p]}</Link>)}
        </div>
      </section>
      <section className={card}>
        <h2 className="font-semibold">Replay timed</h2>
        <p className="mb-3 text-sm text-slate-600">Like Bluebook: R&W 25 in 30 minutes, Math 10 in 16 minutes. Mark for review, cross out choices, see your time sinks at the end.</p>
        <div className="flex flex-wrap gap-2">
          <Link to="/triage?replay=rw" className={btn}>R&W timed</Link>
          <Link to="/triage?replay=math" className={btn}>Math timed</Link>
          <Link to="/triage?replay=both" className={btn}>Both</Link>
        </div>
      </section>
      <p className="text-sm text-slate-600">Your 35 PT6 mistakes, with the trap and the lesson for each, are in <Link to="/mistakes" className="underline">Mistakes</Link>.</p>
    </div>
  );
}

function Practice({ part, onDone }: { part: Part; onDone: () => void }) {
  const list = useQuery({ queryKey: ["pt6-replay", part], queryFn: () => api<Question[]>(`/pt6/replay${part === "all" ? "" : `?section=${part}`}`) });
  if (list.isPending) return <p className="text-slate-500">Loading…</p>;
  if (list.isError || !list.data.length) return <p role="alert" className="text-red-700">Couldn't load the replay questions.</p>;
  const qs = list.data;
  return (
    <Session
      count={qs.length}
      mode="drill"
      doneLabel="Back to PT6 Replay"
      fetchNext={async (exclude) => ({ question: qs.find((q) => !exclude.includes(q.id)) ?? qs[0] })}
      onDone={onDone}
    />
  );
}

export function Pt6() {
  const [params, setParams] = useSearchParams();
  const qc = useQueryClient();
  const part = params.get("practice");
  const back = () => {
    void qc.invalidateQueries({ queryKey: ["skills"] });
    setParams({});
    window.scrollTo(0, 0);
  };
  return (
    <Shell>
      {part === "rw" || part === "math" || part === "all" ? <Practice key={part} part={part} onDone={back} /> : <Overview />}
    </Shell>
  );
}
