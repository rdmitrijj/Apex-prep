import { useState } from "react";
import { api } from "../api/client";

export const REASONS = [
  ["concept", "Didn't know how"],
  ["careless", "Careless slip"],
  ["misread", "Misread the question"],
  ["time", "Rushed / out of time"],
  ["guess", "Guessed"],
] as const;
export type Reason = (typeof REASONS)[number][0];

export const tagReason = (responseId: number, reason: Reason | null) =>
  api<void>(`/responses/${responseId}/reason`, { method: "PUT", json: { miss_reason: reason } });

// "Why did you miss it?" chips: the tag feeds the Mistake Notebook filters.
export function MissReason({ responseId, initial = null }: { responseId: number; initial?: string | null }) {
  const [reason, setReason] = useState<string | null>(initial);
  const [err, setErr] = useState(false);
  const pick = (r: Reason) => {
    const next = reason === r ? null : r;
    setReason(next);
    tagReason(responseId, next).then(() => setErr(false), () => setErr(true));
  };
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Why did you miss it?">
      <span className="text-slate-600">Why did you miss it?</span>
      {REASONS.map(([id, label]) => (
        <button key={id} type="button" aria-pressed={reason === id} onClick={() => pick(id)} className={`rounded-full border px-3 py-0.5 ${reason === id ? "border-brand-700 bg-brand-700 text-white" : "border-slate-300 hover:border-brand-500"}`}>
          {label}
        </button>
      ))}
      {err && <span role="alert" className="text-xs text-red-700">Couldn't save.</span>}
    </div>
  );
}
