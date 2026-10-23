import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { goalsBody, goalsForm, useMe, type User } from "../api/auth";
import { api, ApiError } from "../api/client";
import { GoalFields } from "../components/GoalFields";
import { Shell } from "../components/Shell";

export function Goals() {
  const me = useMe();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [form, setForm] = useState(() => goalsForm(me.data));
  const save = useMutation({
    mutationFn: () => api<User>("/auth/me/goals", { method: "PUT", json: goalsBody(form) }),
    onSuccess: (user) => {
      qc.setQueryData(["me"], user);
      qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "me" }); // plan and weaknesses depend on goals
      navigate("/");
    },
  });
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  const error = save.error instanceof ApiError ? save.error.message : save.error ? "Network error" : null;

  return (
    <Shell>
      <form onSubmit={onSubmit} className="max-w-md space-y-4 rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h1 className="text-2xl font-bold">Your goals</h1>
        {!me.data?.target_total && <p className="text-slate-600">Tell us what you're aiming for so the plan can adapt to you.</p>}
        <GoalFields value={form} onChange={setForm} />
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <button type="submit" disabled={save.isPending} className="rounded-md bg-brand-700 px-5 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-60">
          Save goals
        </button>
      </form>
    </Shell>
  );
}
