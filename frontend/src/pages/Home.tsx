import { useState } from "react";
import { Link } from "react-router-dom";
import { Shell } from "../components/Shell";

const TEST_DAY = new Date("2026-12-05T08:00:00");

export function Home() {
  const [days] = useState(() => Math.max(0, Math.ceil((TEST_DAY.getTime() - Date.now()) / 86_400_000)));
  return (
    <Shell>
      <div className="mx-auto max-w-3xl space-y-6">
        <section className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm uppercase tracking-wide text-slate-500">Test day · 5 December 2026</p>
          <p className="mt-1 text-4xl font-bold text-brand-700">{days} days left</p>
        </section>
        <Link to="/drill" className="block rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200 hover:ring-brand-500">
          <p className="text-lg font-semibold">Topic Drill</p>
          <p className="text-sm text-slate-600">Pick skills and a difficulty, get instant feedback with worked solutions.</p>
        </Link>
      </div>
    </Shell>
  );
}
