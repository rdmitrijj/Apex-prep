import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useMe } from "../api/auth";
import { api } from "../api/client";
import { Logo } from "./Logo";
import { Settings } from "./Settings";

// Per-device preference; the exam runner has no Shell, so exams stay light like the real test.
const THEME_KEY = "apex-theme";
function storedDark() {
  try {
    return localStorage.getItem(THEME_KEY) === "dark";
  } catch {
    return false;
  }
}

const link = ({ isActive }: { isActive: boolean }) => (isActive ? "font-semibold text-brand-700" : "text-slate-600 hover:text-brand-700");

export function Shell({ children }: { children: ReactNode }) {
  const me = useMe();
  const qc = useQueryClient();
  const [dark, setDark] = useState(storedDark);
  const toggleDark = (on: boolean) => {
    setDark(on);
    try {
      localStorage.setItem(THEME_KEY, on ? "dark" : "light");
    } catch {
      /* storage blocked: the choice lasts for this page only */
    }
  };
  const logout = useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      qc.setQueryData(["me"], null); // redirects to /login
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" }); // drop this account's cached data
    },
  });
  return (
    <div className={`min-h-screen bg-slate-50 text-slate-900 ${dark ? "dark" : ""}`}>
      <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-6 py-3">
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
          <NavLink to="/" className="flex items-center gap-2 text-base font-semibold text-brand-900">
            <Logo className="h-7 w-7" /> Apex Prep
          </NavLink>
          <NavLink to="/plan" className={link}>
            Plan
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
          <NavLink to="/triage" className={link}>
            Triage
          </NavLink>
          <NavLink to="/mistakes" className={link}>
            Mistakes
          </NavLink>
        </nav>
        <div className="flex items-center gap-4 text-sm">
          <span className="hidden text-slate-600 sm:inline">{me.data?.email}</span>
          <NavLink to="/goals" className={link}>
            Goals
          </NavLink>
          <Settings dark={dark} onDark={toggleDark} onSignOut={() => logout.mutate()} />
        </div>
      </header>
      <main className="mx-auto max-w-5xl p-6">{children}</main>
    </div>
  );
}
