import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useMe } from "../api/auth";
import { api } from "../api/client";
import { Logo } from "../components/Logo";

const TEST_DAY = new Date("2026-12-05T08:00:00");

export function Home() {
  const me = useMe();
  const qc = useQueryClient();
  const logout = useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => qc.setQueryData(["me"], null),
  });
  const [days] = useState(() => Math.max(0, Math.ceil((TEST_DAY.getTime() - Date.now()) / 86_400_000)));

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <div className="flex items-center gap-2 font-semibold text-brand-900">
          <Logo className="h-7 w-7" /> Apex Prep
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-slate-600">{me.data?.email}</span>
          <button onClick={() => logout.mutate()} className="text-brand-700 hover:underline">
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl p-6">
        <section className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm uppercase tracking-wide text-slate-500">Test day · 5 December 2026</p>
          <p className="mt-1 text-4xl font-bold text-brand-700">{days} days left</p>
        </section>
      </main>
    </div>
  );
}
