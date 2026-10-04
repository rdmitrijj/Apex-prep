import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useMe } from "../api/auth";
import { api } from "../api/client";
import { Logo } from "./Logo";

const link = ({ isActive }: { isActive: boolean }) => (isActive ? "font-semibold text-brand-700" : "text-slate-600 hover:text-brand-700");

export function Shell({ children }: { children: ReactNode }) {
  const me = useMe();
  const qc = useQueryClient();
  const logout = useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => qc.setQueryData(["me"], null),
  });
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-6 py-3">
        <nav className="flex items-center gap-6 text-sm">
          <NavLink to="/" className="flex items-center gap-2 text-base font-semibold text-brand-900">
            <Logo className="h-7 w-7" /> Apex Prep
          </NavLink>
          <NavLink to="/exam" className={link}>
            Practice Exam
          </NavLink>
          <NavLink to="/drill" className={link}>
            Topic Drill
          </NavLink>
          <NavLink to="/training" className={link}>
            Weakness Training
          </NavLink>
          <NavLink to="/mistakes" className={link}>
            Mistakes
          </NavLink>
        </nav>
        <div className="flex items-center gap-4 text-sm">
          <span className="hidden text-slate-600 sm:inline">{me.data?.email}</span>
          <button onClick={() => logout.mutate()} className="text-brand-700 hover:underline">
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl p-6">{children}</main>
    </div>
  );
}
