import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fmtDate } from "../api/exam";
import { nextInSet, useDrillSets, type DrillSet } from "../api/pt5";
import { RuleCard } from "../components/RuleCard";
import { Shell } from "../components/Shell";
import { Session } from "./Drill";

const card = "rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200";

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.round(100 * value);
  return (
    <div role="progressbar" aria-label={label} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
      <div className={`h-full ${value >= 1 ? "bg-emerald-600" : "bg-brand-600"}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function status(s: DrillSet) {
  if (s.review_due) return <span className="font-medium text-amber-700">Review due</span>;
  if (s.mastered) return <span className="text-emerald-700">Mastered · review {s.review_due_at ? fmtDate(s.review_due_at) : "soon"}</span>;
  if (!s.recent_total) return <span className="text-slate-500">Not started</span>;
  return (
    <span className="text-slate-600">
      Last {s.recent_total}: {s.recent_correct} right · {s.days} {s.days === 1 ? "day" : "days"}
    </span>
  );
}

function SetRow({ s }: { s: DrillSet }) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3">
      <div className="min-w-48 flex-1">
        <p className="font-medium">{s.name}</p>
        <p className="text-xs">{status(s)}</p>
      </div>
      <div className="w-32"><Bar value={s.progress} label={`${s.name} progress`} /></div>
      <Link to={`/pt5?set=${s.id}`} className="rounded-md border border-brand-700 px-3 py-1 text-sm text-brand-700 hover:bg-brand-50">
        {s.review_due ? "Review" : s.answered ? "Continue" : "Start"}
      </Link>
    </li>
  );
}

function Overview({ sets, readiness }: { sets: DrillSet[]; readiness: number }) {
  const due = sets.filter((s) => s.review_due);
  const mastered = sets.filter((s) => s.mastered).length;
  return (
    <div className="space-y-6">
      <div className="max-w-2xl space-y-2">
        <h1 className="text-2xl font-bold">PT5 Weakness Drill</h1>
        <p className="text-slate-700">
          One mini-set for each weakness from Practice Test 5. Each set starts with a rule card. A set is <strong>mastered</strong> when you get at least 7 of your last 8 right,
          on two different days; then it comes back for review after 1, 3, and 7 days.
        </p>
      </div>
      <section className={card}>
        <div className="flex items-baseline justify-between">
          <h2 className="font-semibold">Readiness</h2>
          <span className="text-3xl font-bold text-brand-700">{Math.round(100 * readiness)}%</span>
        </div>
        <div className="mt-2"><Bar value={readiness} label="Overall readiness" /></div>
        <p className="mt-2 text-sm text-slate-600">
          {mastered} of {sets.length} sets mastered.{" "}
          <Link to="/pt5?cards=1" className="underline">Warm-up: rule cards only</Link> · <Link to="/triage" className="underline">Mini Mock</Link>
        </p>
      </section>
      {due.length > 0 && (
        <section className={`${card} ring-amber-300`}>
          <h2 className="font-semibold">Due for review</h2>
          <ul className="divide-y divide-slate-100">{due.map((s) => <SetRow key={s.id} s={s} />)}</ul>
        </section>
      )}
      {(["RW", "MATH"] as const).map((sec) => (
        <section key={sec} className={card}>
          <h2 className="font-semibold">{sec === "RW" ? "Reading and Writing" : "Math"}</h2>
          <ul className="divide-y divide-slate-100">
            {sets.filter((s) => s.section === sec).sort((a, b) => a.priority - b.priority).map((s) => <SetRow key={s.id} s={s} />)}
          </ul>
        </section>
      ))}
    </div>
  );
}

function SetView({ s, onBack }: { s: DrillSet; onBack: () => void }) {
  const [started, setStarted] = useState(false);
  if (started)
    return (
      <Session
        count={s.count}
        mode="drill"
        doneLabel="Back to the sets"
        fetchNext={async (exclude) => ({ question: (await nextInSet(s.id, exclude)).question })}
        onDone={onBack}
      />
    );
  return (
    <div className="max-w-2xl space-y-4">
      <div className={card}><RuleCard markdown={s.rule} /></div>
      <div className="flex items-center gap-4">
        <button type="button" autoFocus onClick={() => setStarted(true)} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">
          Start the {s.count} questions
        </button>
        <button type="button" onClick={onBack} className="text-sm text-slate-600 hover:underline">Back to the sets</button>
      </div>
      <p className="text-sm text-slate-600">Medium questions first, then hard. Questions you haven't seen come first; you can stop at any time.</p>
    </div>
  );
}

function Cards({ sets }: { sets: DrillSet[] }) {
  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Warm-up: rule cards</h1>
      <p className="text-slate-700">Read each card once, slowly. No questions today.</p>
      {[...sets].sort((a, b) => a.priority - b.priority || a.section.localeCompare(b.section)).map((s) => (
        <div key={s.id} className={card}><RuleCard markdown={s.rule} /></div>
      ))}
      <Link to="/pt5" className="inline-block rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600">Done</Link>
    </div>
  );
}

export function Pt5Drill() {
  const [params, setParams] = useSearchParams();
  const data = useDrillSets();
  const qc = useQueryClient();
  const s = data.data?.sets.find((x) => x.id === params.get("set"));
  const back = () => {
    void qc.invalidateQueries({ queryKey: ["pt5-sets"] });
    setParams({});
    window.scrollTo(0, 0);
  };
  return (
    <Shell>
      {data.isPending && <p className="text-slate-500">Loading…</p>}
      {data.isError && <p role="alert" className="text-red-700">Couldn't load the drill sets.</p>}
      {data.data && (params.get("cards") ? <Cards sets={data.data.sets} /> : s ? <SetView key={s.id} s={s} onBack={back} /> : <Overview {...data.data} />)}
    </Shell>
  );
}
