import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { createExam, fmtDate, SECTION_NAME, useExams, type Section, type Setting } from "../api/exam";
import { OfficialScores } from "../components/OfficialScores";
import { Shell } from "../components/Shell";

const SETTINGS: { id: Setting; name: string; desc: string }[] = [
  { id: "official", name: "Official-level", desc: "Same difficulty mix as the real test." },
  { id: "hard", name: "Hard", desc: "More hard questions in every module." },
  { id: "brutal", name: "Brutal", desc: "Mostly hard questions. Good practice for a 700+ Math target." },
];
const SCOPES: { id: string; name: string; sections: Section[]; time: string }[] = [
  { id: "full", name: "Full test", sections: ["RW", "MATH"], time: "2 h 14 min + 10 min break" },
  { id: "rw", name: "Reading and Writing only", sections: ["RW"], time: "64 min" },
  { id: "math", name: "Math only", sections: ["MATH"], time: "70 min" },
];

export function ExamHome() {
  const exams = useExams();
  const navigate = useNavigate();
  const [setting, setSetting] = useState<Setting>("official");
  const [scope, setScope] = useState("full");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const active = exams.data?.find((e) => e.status === "in_progress");

  const start = () => {
    if (active && !window.confirm("Starting a new exam discards the one in progress. Continue?")) return;
    setBusy(true);
    setErr(null);
    createExam({ difficulty: setting, sections: SCOPES.find((s) => s.id === scope)!.sections }).then(
      ({ id }) => navigate(`/exam/${id}`),
      (e) => {
        setErr(e instanceof ApiError ? e.message : "Network error, try again.");
        setBusy(false);
      },
    );
  };

  return (
    <Shell>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Practice Exam</h1>
        {active && (
          <div className="flex items-center justify-between rounded-xl bg-amber-50 p-4 ring-1 ring-amber-200">
            <span>You have an exam in progress ({active.sections.map((s) => SECTION_NAME[s]).join(" + ")}, {active.difficulty}).</span>
            <Link to={`/exam/${active.id}`} className="rounded-md bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600">Resume</Link>
          </div>
        )}
        <div className="grid gap-6 rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200 md:grid-cols-2">
          <fieldset className="space-y-2">
            <legend className="mb-2 font-semibold">What to take</legend>
            {SCOPES.map((s) => (
              <label key={s.id} className="flex cursor-pointer items-start gap-2">
                <input type="radio" name="scope" checked={scope === s.id} onChange={() => setScope(s.id)} className="mt-1" />
                <span>{s.name}<span className="block text-sm text-slate-500">{s.time}</span></span>
              </label>
            ))}
          </fieldset>
          <fieldset className="space-y-2">
            <legend className="mb-2 font-semibold">Difficulty</legend>
            {SETTINGS.map((s) => (
              <label key={s.id} className="flex cursor-pointer items-start gap-2">
                <input type="radio" name="setting" checked={setting === s.id} onChange={() => setSetting(s.id)} className="mt-1" />
                <span>{s.name}<span className="block text-sm text-slate-500">{s.desc}</span></span>
              </label>
            ))}
          </fieldset>
          <div className="space-y-2 md:col-span-2">
            <p className="text-sm text-slate-600">
              Adaptive like the real test: how you do in Module 1 decides whether Module 2 is easier or harder. The timer runs on the server, and your answers save as you go, so you can close the tab and resume later.
            </p>
            {err && <p role="alert" className="text-red-700">{err}</p>}
            <button onClick={start} disabled={busy} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50">
              {busy ? "Building your exam…" : "Start exam"}
            </button>
          </div>
        </div>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Past exams</h2>
          {exams.isPending && <p className="text-slate-500">Loading…</p>}
          {exams.data?.filter((e) => e.status === "completed").length === 0 && <p className="text-slate-500">No finished exams yet.</p>}
          <ul className="divide-y divide-slate-200 rounded-xl bg-white shadow-sm ring-1 ring-slate-200 empty:hidden">
            {exams.data
              ?.filter((e) => e.status === "completed")
              .map((e) => (
                <li key={e.id}>
                  <Link to={`/exam/${e.id}/results`} className="flex items-center justify-between px-4 py-3 hover:bg-slate-50">
                    <span>
                      {fmtDate(e.completed_at ?? e.created_at)} · {e.sections.length === 2 ? "Full test" : SECTION_NAME[e.sections[0]]} · <span className="capitalize">{e.difficulty}</span>
                    </span>
                    <span className="font-mono text-sm">
                      {e.rw_score !== null && <>R&W {e.rw_score} </>}
                      {e.math_score !== null && <>Math {e.math_score} </>}
                      {e.rw_score !== null && e.math_score !== null && <strong>= {e.rw_score + e.math_score}</strong>}
                    </span>
                  </Link>
                </li>
              ))}
          </ul>
        </section>
        <OfficialScores />
      </div>
    </Shell>
  );
}
