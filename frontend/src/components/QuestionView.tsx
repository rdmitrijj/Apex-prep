import { useState } from "react";
import { reportQuestion, validSpr, type Feedback, type Question } from "../api/drill";
import { Figure } from "./Figure";
import { MathText } from "./MathText";

const LETTERS = ["A", "B", "C", "D"];

export function Passage({ q }: { q: Question }) {
  return (
    <div className="space-y-3 leading-relaxed">
      {q.passage2 && <p className="text-sm font-semibold">Text 1</p>}
      {q.passage && <p className="whitespace-pre-line"><MathText text={q.passage} /></p>}
      {q.passage2 && (
        <>
          <p className="text-sm font-semibold">Text 2</p>
          <p className="whitespace-pre-line"><MathText text={q.passage2} /></p>
        </>
      )}
      {q.notes && (
        <ul className="list-disc space-y-1 pl-5">
          {q.notes.map((n, i) => <li key={i}><MathText text={n} /></li>)}
        </ul>
      )}
      {q.figure && <Figure spec={q.figure} />}
    </div>
  );
}

function Report({ id }: { id: number }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [state, setState] = useState<"idle" | "sent" | "error">("idle");
  if (state === "sent") return <p className="text-xs text-slate-500">Thanks. This question is hidden until it's reviewed.</p>;
  if (!open)
    return (
      <button type="button" onClick={() => setOpen(true)} className="text-xs text-slate-500 hover:underline">
        Report a problem
      </button>
    );
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        reportQuestion(id, reason).then(() => setState("sent"), () => setState("error"));
      }}
    >
      <input aria-label="What's wrong?" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="What's wrong?" minLength={3} required className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm" />
      <button className="rounded bg-slate-700 px-3 text-sm text-white">Send</button>
      {state === "error" && <span role="alert" className="text-xs text-red-700">Couldn't send.</span>}
    </form>
  );
}

export function QuestionView({
  q,
  feedback,
  busy,
  error,
  onSubmit,
  given = null,
}: {
  q: Question;
  feedback: Feedback | null;
  busy: boolean;
  error: string | null;
  onSubmit: (answer: string) => void;
  given?: string | null; // review mode: the answer given earlier
}) {
  const [choice, setChoice] = useState<string | null>(q.format === "mc" ? given : null);
  const [entry, setEntry] = useState(q.format === "spr" ? (given ?? "") : "");
  const isRW = q.skill_id.startsWith("RW");
  const sprOk = validSpr(entry.trim());
  const canSubmit = !feedback && !busy && (q.format === "mc" ? choice !== null : sprOk);
  const submit = () => canSubmit && onSubmit(q.format === "mc" ? choice! : entry.trim());

  const question = (
    <div className="space-y-4">
      {!isRW && q.figure && <Figure spec={q.figure} />}
      <p className="leading-relaxed"><MathText text={q.stem} /></p>
      {q.format === "mc" ? (
        <div role="radiogroup" aria-label="Answer choices" className="space-y-2">
          {q.choices!.map((c, i) => {
            const L = LETTERS[i];
            const isKey = feedback?.answer === L;
            const picked = choice === L;
            const tone = feedback
              ? isKey
                ? "border-emerald-600 bg-emerald-50"
                : picked
                  ? "border-red-600 bg-red-50"
                  : "border-slate-200"
              : picked
                ? "border-brand-600 bg-brand-50 ring-2 ring-brand-500"
                : "border-slate-300 hover:border-brand-500";
            return (
              <div key={L}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={picked}
                  disabled={!!feedback}
                  onClick={() => setChoice(L)}
                  className={`flex w-full items-start gap-3 rounded-lg border-2 px-3 py-2 text-left ${tone}`}
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-current text-sm font-semibold">{L}</span>
                  <MathText text={c} />
                </button>
                {feedback && feedback.rationales[L] && (
                  <p className={`ml-9 mt-1 text-sm ${isKey ? "text-emerald-800" : "text-slate-600"}`}>
                    <MathText text={feedback.rationales[L]} />
                  </p>
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
            onChange={(e) => setEntry(e.target.value.replace(/[^0-9./-]/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            maxLength={6}
            inputMode="decimal"
            aria-label="Your answer"
            disabled={!!feedback}
            className="mt-1 block w-40 rounded-md border border-slate-300 px-3 py-2 font-mono text-lg"
          />
          <span className="text-xs text-slate-500">
            Fraction (7/2) or decimal (3.5). Up to 5 characters, 6 if negative. Fill every character for long decimals.
          </span>
        </label>
      )}
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      {feedback ? (
        <div className={`rounded-lg p-4 ${feedback.correct ? "bg-emerald-50" : "bg-red-50"}`}>
          <p className="font-semibold">
            {feedback.correct ? "Correct" : "Not quite"}
            {q.format === "spr" && <span className="font-normal">: answer {feedback.answer}</span>}
          </p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
            {feedback.explanation.map((s, i) => <li key={i}><MathText text={s} /></li>)}
          </ol>
        </div>
      ) : (
        <button type="button" onClick={submit} disabled={!canSubmit} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50">
          Check answer
        </button>
      )}
      <div>
        <Report key={q.id} id={q.id} />
      </div>
    </div>
  );

  if (!isRW) return question;
  return (
    <div className="grid gap-6 md:grid-cols-2 md:divide-x md:divide-slate-200">
      <Passage q={q} />
      <div className="md:pl-6">{question}</div>
    </div>
  );
}
