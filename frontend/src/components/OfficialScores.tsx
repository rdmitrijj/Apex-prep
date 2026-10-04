import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import { addOfficialScore, deleteOfficialScore, fmtDate, useOfficialScores, type Section } from "../api/exam";

const today = () => new Date().toISOString().slice(0, 10);
const NAME: Record<Section, string> = { RW: "R&W", MATH: "Math" };

export function OfficialScores() {
  const qc = useQueryClient();
  const list = useOfficialScores();
  const [form, setForm] = useState({ taken_on: today(), kind: "practice", label: "", rw: "", math: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = () => {
    for (const key of ["official-scores", "exams", "exam-results"]) qc.invalidateQueries({ queryKey: [key] });
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    addOfficialScore({ ...form, rw: Number(form.rw), math: Number(form.math) })
      .then(() => {
        setForm((f) => ({ ...f, label: "", rw: "", math: "" }));
        refresh();
      }, (e2) => setErr(e2 instanceof ApiError ? e2.message : "Network error, try again."))
      .finally(() => setBusy(false));
  };
  const remove = (id: number) => {
    if (window.confirm("Delete this score? Your exam estimates will be recalibrated without it.")) deleteOfficialScore(id).then(refresh);
  };
  const cal = list.data?.calibration;
  const input = "rounded border border-slate-300 px-2 py-1";

  return (
    <section id="official" className="scroll-mt-4 space-y-3 rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div>
        <h2 className="text-lg font-semibold">Official scores and calibration</h2>
        <p className="text-sm text-slate-600">
          Log scores from official practice tests and real sittings. Each one is paired with your in-app exam closest in time (within {list.data?.window_days ?? 14} days), and every in-app estimate is re-fitted to them. Two or three pairs at different points in your prep calibrate well.
        </p>
        {cal && (
          <p className="mt-1 text-sm">
            {(Object.keys(NAME) as Section[]).map((s) => (
              <span key={s} className="mr-4">
                {NAME[s]}: {cal[s].pairs ? <span className="text-emerald-700">calibrated from {cal[s].pairs} official {cal[s].pairs === 1 ? "score" : "scores"}</span> : <span className="text-slate-500">default scale (not calibrated yet)</span>}
              </span>
            ))}
          </p>
        )}
      </div>
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col">Date<input type="date" required max={today()} value={form.taken_on} onChange={(e) => setForm({ ...form, taken_on: e.target.value })} className={input} /></label>
        <label className="flex flex-col">Type
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })} className={input}>
            <option value="practice">Official practice test</option>
            <option value="real">Real test day</option>
          </select>
        </label>
        <label className="flex flex-col">Label<input value={form.label} maxLength={100} placeholder="e.g. Practice test 4" onChange={(e) => setForm({ ...form, label: e.target.value })} className={`${input} w-40`} /></label>
        <label className="flex flex-col">R&W<input type="number" required min={200} max={800} step={10} value={form.rw} onChange={(e) => setForm({ ...form, rw: e.target.value })} className={`${input} w-20`} /></label>
        <label className="flex flex-col">Math<input type="number" required min={200} max={800} step={10} value={form.math} onChange={(e) => setForm({ ...form, math: e.target.value })} className={`${input} w-20`} /></label>
        <button disabled={busy} className="rounded-md bg-brand-700 px-4 py-1.5 font-medium text-white hover:bg-brand-600 disabled:opacity-50">Add score</button>
      </form>
      {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
      {list.data && list.data.scores.length > 0 && (
        <ul className="divide-y divide-slate-100 text-sm">
          {list.data.scores.map((o) => {
            const paired = (Object.keys(NAME) as Section[]).filter((s) => o.paired_exam[s]);
            return (
              <li key={o.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  {fmtDate(o.taken_on)} · {o.kind === "real" ? "Real test" : "Practice test"}{o.label && ` · ${o.label}`}
                  <span className="block text-xs text-slate-500">
                    {paired.length ? `Calibrating ${paired.map((s) => NAME[s]).join(" and ")}` : `No in-app exam within ${list.data.window_days} days; take one to use this score`}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="font-mono">R&W {o.rw} · Math {o.math} = <strong>{o.rw + o.math}</strong></span>
                  <button type="button" onClick={() => remove(o.id)} aria-label={`Delete score from ${fmtDate(o.taken_on)}`} className="text-slate-500 hover:text-red-700">✕</button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
