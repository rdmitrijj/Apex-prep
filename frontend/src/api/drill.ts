import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export type Difficulty = "easy" | "medium" | "hard";

export type SkillNode = {
  id: string;
  parent_id: string | null;
  name: string;
  level: "section" | "domain" | "skill" | "subskill";
  section: "RW" | "MATH";
  weight: number;
  generated: boolean;
  available: number;
  attempts: number;
  correct: number;
};

// Figure specs are produced by the backend (math generators and the R&W item schema).
export type FigureSpec =
  | { kind: "table"; title?: string; header: string[]; rows: string[][] }
  | { kind: "bars"; title?: string; labels: string[]; values?: number[]; series?: { name: string; values: number[] }[]; xlabel?: string; ylabel?: string }
  | { kind: "line"; title?: string; x: number[]; series: { name: string; values: number[] }[]; xlabel?: string; ylabel?: string }
  | {
      kind: "plot";
      x: [number, number];
      y: [number, number];
      curves?: [number, number][][];
      polygons?: [number, number][][];
      points?: ([number, number] | [number, number, string])[];
      xlabel?: string;
      ylabel?: string;
    }
  | {
      kind: "shape";
      points: Record<string, [number, number]>;
      segments: [string, string][];
      labels: { at: [number, number]; text: string }[];
      circles?: { c: [number, number]; r: number }[];
      right_angles?: string[];
      hide_points?: boolean;
    };

export type Question = {
  id: number;
  skill_id: string;
  skill_name: string;
  difficulty: Difficulty;
  format: "mc" | "spr";
  stem: string;
  choices: string[] | null;
  passage?: string | null;
  passage2?: string | null;
  notes?: string[] | null;
  figure?: FigureSpec | null;
};

export type Feedback = { correct: boolean; answer: string; explanation: string[]; rationales: Record<string, string> };

export function useSkills() {
  return useQuery({ queryKey: ["skills"], queryFn: () => api<SkillNode[]>("/skills") });
}

export const nextQuestion = (body: { skill_ids: string[]; difficulty: Difficulty | "mixed"; exclude_ids: number[] }) =>
  api<Question>("/drill/next", { method: "POST", json: body });

export const submitAnswer = (body: { question_id: number; answer: string; time_ms: number; mode?: "drill" | "training" }) =>
  api<Feedback>("/drill/answer", { method: "POST", json: body });

export const reportQuestion = (id: number, reason: string) =>
  api<void>(`/questions/${id}/report`, { method: "POST", json: { reason } });

// Mirrors backend app/generators/spr.py:is_valid_entry (official SPR entry rules).
export function validSpr(entry: string): boolean {
  return /^-?(\d+|\d+\.\d*|\.\d+|\d+\/\d+)$/.test(entry) && entry.length <= (entry.startsWith("-") ? 6 : 5);
}
