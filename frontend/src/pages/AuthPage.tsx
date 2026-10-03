import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useMe, type User } from "../api/auth";
import { api, ApiError } from "../api/client";
import { Logo } from "../components/Logo";

export function AuthPage() {
  const me = useMe();
  const qc = useQueryClient();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const submit = useMutation({
    mutationFn: () => api<User>(`/auth/${mode}`, { method: "POST", json: { email, password } }),
    onSuccess: (user) => qc.setQueryData(["me"], user),
  });

  if (me.data) return <Navigate to="/" replace />;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit.mutate();
  };
  const error = submit.error instanceof ApiError ? submit.error.message : submit.error ? "Network error" : null;

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 rounded-xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <div className="flex items-center gap-3">
          <Logo />
          <h1 className="text-xl font-semibold">{mode === "login" ? "Sign in to Apex Prep" : "Create your account"}</h1>
        </div>
        <label className="block">
          <span className="text-sm font-medium">Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:outline-2 focus:outline-brand-500"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Password</span>
          <input
            type="password"
            required
            minLength={mode === "register" ? 10 : 1}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:outline-2 focus:outline-brand-500"
          />
          {mode === "register" && <span className="text-xs text-slate-500">At least 10 characters.</span>}
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submit.isPending}
          className="w-full rounded-md bg-brand-700 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-60"
        >
          {mode === "login" ? "Sign in" : "Create account"}
        </button>
        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            submit.reset();
          }}
          className="w-full text-sm text-brand-700 hover:underline"
        >
          {mode === "login" ? "No account yet? Register" : "Have an account? Sign in"}
        </button>
      </form>
    </main>
  );
}
