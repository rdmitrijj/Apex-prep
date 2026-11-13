import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { Question } from "./drill";

export type DrillSet = {
  id: string;
  name: string;
  section: "RW" | "MATH";
  priority: number;
  count: number;
  answered: number;
  recent_correct: number;
  recent_total: number;
  days: number;
  mastered: boolean;
  progress: number;
  review_due_at: string | null;
  review_due: boolean;
  miss_reason: string;
  rule: string;
};
export type PlanItem = { key: string; text: string; link: string | null; done: boolean };
export type Plan = { visible: boolean; title: string; days: { date: string; title: string; items: PlanItem[] }[] };

export const useDrillSets = () => useQuery({ queryKey: ["pt5-sets"], queryFn: () => api<{ readiness: number; sets: DrillSet[] }>("/pt5/sets") });
export const nextInSet = (id: string, exclude: number[]) =>
  api<{ question: Question; position: number; total: number }>(`/pt5/sets/${id}/next`, { method: "POST", json: { exclude_ids: exclude } });
export const useStudyPlan = () => useQuery({ queryKey: ["pt5-plan"], queryFn: () => api<Plan>("/pt5/plan") });
export const checkPlan = (key: string, done: boolean) => api<void>(`/pt5/plan/${key}`, { method: "PUT", json: { done } });
