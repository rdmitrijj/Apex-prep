import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { Difficulty, Question } from "./drill";

export type Section = "RW" | "MATH";
export type Setting = "official" | "hard" | "brutal";

export type ItemState = { answer: string | null; flagged: boolean; eliminated: string[]; time_ms: number };
export type ExamItem = ItemState & { id: number; position: number; question: Question };

export type ExamState = {
  id: number;
  status: "in_progress" | "completed" | "abandoned";
  difficulty: Setting;
  sections: Section[];
  total_modules: number;
  module: {
    id: number;
    section: Section;
    stage: number;
    index: number;
    started: boolean;
    remaining_ms: number | null;
    items: ExamItem[];
  } | null;
  break_remaining_ms: number | null;
};

export type ExamSummary = {
  id: number;
  status: ExamState["status"];
  difficulty: Setting;
  sections: Section[];
  created_at: string;
  completed_at: string | null;
  rw_score: number | null;
  math_score: number | null;
};

export type ReviewItem = {
  response_id: number | null;
  miss_reason: string | null;
  module: string;
  section: Section;
  position: number;
  pretest: boolean;
  question: Question;
  difficulty: Difficulty;
  answer: string | null;
  correct: boolean;
  key: string;
  time_ms: number;
  flagged: boolean;
  explanation: string[];
  rationales: Record<string, string>;
};

export type ExamResults = ExamSummary & {
  margins: Partial<Record<Section, number>>;
  calibrated_with: Partial<Record<Section, number>>;
  breakdown: { id: string; name: string; level: string; section: Section; correct: number; total: number }[];
  items: ReviewItem[];
};

export const SECTION_NAME: Record<Section, string> = { RW: "Reading and Writing", MATH: "Math" };
export const MODULE_MINUTES: Record<Section, number> = { RW: 32, MATH: 35 };
export const MODULE_QUESTIONS: Record<Section, number> = { RW: 27, MATH: 22 };
// Per-question time budget on the real test.
export const TARGET_SECONDS: Record<Section, number> = { RW: (32 * 60) / 27, MATH: (35 * 60) / 22 };

export const createExam = (body: { difficulty: Setting; sections: Section[] }) =>
  api<{ id: number }>("/exams", { method: "POST", json: body });
export const startModule = (id: number) => api<ExamState>(`/exams/${id}/start`, { method: "POST" });
export const submitModule = (id: number) => api<ExamState>(`/exams/${id}/submit-module`, { method: "POST" });
export const saveItem = (examId: number, itemId: number, body: ItemState) =>
  api<void>(`/exams/${examId}/items/${itemId}`, { method: "PUT", json: body });

export const useExams = () => useQuery({ queryKey: ["exams"], queryFn: () => api<ExamSummary[]>("/exams") });
export const useExamState = (id: number) =>
  useQuery({ queryKey: ["exam", id], queryFn: () => api<ExamState>(`/exams/${id}`), refetchOnWindowFocus: false });
export const useExamResults = (id: number) =>
  useQuery({ queryKey: ["exam-results", id], queryFn: () => api<ExamResults>(`/exams/${id}/results`) });

export type WeaknessRow = {
  skill_id: string;
  name: string;
  section: Section;
  score: number;
  attempts: number;
  correct: number;
  avg_seconds: number | null;
  target_seconds: number;
  reasons: string[];
};

export const useWeaknesses = (limit = 10) =>
  useQuery({ queryKey: ["weaknesses", limit], queryFn: () => api<WeaknessRow[]>(`/weaknesses?limit=${limit}`) });

export const trainingNext = (body: { exclude_ids: number[]; section: Section | null }) =>
  api<{ question: Question; reasons: string[] }>("/training/next", { method: "POST", json: body });

export function fmtClock(ms: number) {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export const fmtDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

export type OfficialScore = {
  id: number;
  taken_on: string;
  kind: "practice" | "real";
  label: string;
  rw: number;
  math: number;
  paired_exam: Partial<Record<Section, number>>;
};
export type OfficialList = {
  scores: OfficialScore[];
  calibration: Record<Section, { pairs: number; intercept: number; slope: number }>;
  window_days: number;
};

export const useOfficialScores = () =>
  useQuery({ queryKey: ["official-scores"], queryFn: () => api<OfficialList>("/official-scores") });
export const addOfficialScore = (body: { taken_on: string; kind: string; label: string; rw: number; math: number }) =>
  api<{ id: number }>("/official-scores", { method: "POST", json: body });
export const deleteOfficialScore = (id: number) => api<void>(`/official-scores/${id}`, { method: "DELETE" });
