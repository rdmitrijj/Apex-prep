import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { Question } from "./drill";

export type TriageMode = "sprint" | "module" | "weakness" | "math";

export const MODE_INFO: Record<TriageMode, { name: string; blurb: string }> = {
  sprint: { name: "R&W Sprint", blurb: "12 hard questions in 14 minutes, weighted toward Information and Ideas and Words in Context." },
  module: { name: "Module Simulation", blurb: "27 questions in 32 minutes, mostly hard, in the real test's order." },
  weakness: { name: "Weakness Sprint", blurb: "10 hard questions from your two weakest R&W skills, in 12 minutes." },
  math: { name: "Math Sprint", blurb: "10 Math questions in 12 minutes, a little faster than the real pace." },
};

export type TriageQuestion = { question: Question; target_seconds: number };
export type Started = { mode: TriageMode; limit_seconds: number; questions: TriageQuestion[] };

export type VocabEntry = { word: string; pos: string; meaning_en: string; meaning_ru: string; example: string };
export type Group = { id: string; name: string; total: number; correct: number; avg_seconds: number; target_seconds: number };
export type ItemResult = {
  response_id: number;
  question: Question;
  answer: string | null;
  key: string;
  correct: boolean;
  seconds: number;
  target_seconds: number;
  time_sink: boolean;
  flagged: boolean;
  first_pass: boolean;
  explanation: string[];
  rationales: Record<string, string>;
  vocab: VocabEntry[];
};
export type SessionSummary = {
  id: number;
  mode: TriageMode;
  created_at: string;
  limit_seconds: number;
  elapsed_seconds: number;
  total: number;
  correct: number;
  blanks: number;
  avg_seconds: number;
};
export type Results = SessionSummary & {
  by_domain: Group[];
  by_skill: Group[];
  time_sinks: { skill_id: string; name: string; count: number }[];
  first_pass: [number, number];
  second_pass: [number, number];
  recommendations: string[];
  items: ItemResult[];
};

export type SubmitItem = { question_id: number; answer: string | null; time_ms: number; flagged: boolean; first_pass: boolean; eliminated: string[] };

export const startTriage = (mode: TriageMode) => api<Started>("/triage/start", { method: "POST", json: { mode } });
export const submitTriage = (body: { mode: TriageMode; elapsed_ms: number; items: SubmitItem[] }) =>
  api<Results>("/triage/sessions", { method: "POST", json: body });
export const useTriageHistory = () => useQuery({ queryKey: ["triage-history"], queryFn: () => api<SessionSummary[]>("/triage/sessions") });

// Soft per-question timer (mirrors backend engine/triage.timer_color): amber at the target, red 30 s past it.
export const OVER_RED = 30;
export function timerColor(spentS: number, targetS: number): "normal" | "amber" | "red" {
  if (spentS >= targetS + OVER_RED) return "red";
  return spentS >= targetS ? "amber" : "normal";
}

// The final answer counts as first-pass when it was already chosen the first time the student left
// the question (or the student never left it). `firstLeft` is the answer at that moment.
export function isFirstPass(answer: string | null, firstLeft: string | null | undefined): boolean {
  return firstLeft === undefined || (answer !== null && firstLeft === answer);
}

const cell = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);

// Anki CSV (same columns as exports/wic_vocab.csv) for the words in the words-in-context questions missed.
export function missedVocabCsv(items: ItemResult[]): string | null {
  const seen = new Map<string, VocabEntry>();
  for (const it of items) if (!it.correct) for (const v of it.vocab) if (!seen.has(v.word.toLowerCase())) seen.set(v.word.toLowerCase(), v);
  if (!seen.size) return null;
  const rows = [["word", "part_of_speech", "meaning_en", "meaning_ru", "example_sentence"], ...[...seen.values()].map((v) => [v.word, v.pos, v.meaning_en, v.meaning_ru, v.example])];
  return rows.map((r) => r.map(cell).join(",")).join("\n") + "\n";
}
