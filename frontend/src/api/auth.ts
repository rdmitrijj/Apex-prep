import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "./client";

export type User = {
  id: number;
  email: string;
  test_date: string | null;
  target_total: number | null;
  target_math: number | null; // optional section minimums
  target_rw: number | null;
  section_targets: { MATH: number; RW: number } | null;
};

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<User>("/auth/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: Infinity,
  });
}

// Goal form state: input values as typed; empty section minimums mean "none".
export type GoalsForm = { test_date: string; target_total: string; target_math: string; target_rw: string };

export const goalsForm = (u?: User | null): GoalsForm => ({
  test_date: u?.test_date ?? "",
  target_total: u?.target_total?.toString() ?? "",
  target_math: u?.target_math?.toString() ?? "",
  target_rw: u?.target_rw?.toString() ?? "",
});

export const goalsBody = (f: GoalsForm) => ({
  test_date: f.test_date,
  target_total: Number(f.target_total),
  target_math: f.target_math ? Number(f.target_math) : null,
  target_rw: f.target_rw ? Number(f.target_rw) : null,
});
