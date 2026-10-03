import { useEffect, useState, type ReactNode } from "react";
import { Logo } from "./Logo";

type State = "checking" | "waking" | "ready" | "down";

const SLOW_MS = 1500; // show the wake-up screen only if the first ping is slow
const RETRY_MS = 3000;
const GIVE_UP_MS = 3 * 60_000; // Render free tier cold starts take ~30-60 s

/** Holds the app until /api/health answers, so a sleeping server reads as "waking up", not as errors. */
export function ServerGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const start = Date.now();
    const slow = setTimeout(() => !cancelled && setState((s) => (s === "checking" ? "waking" : s)), SLOW_MS);
    let retry: ReturnType<typeof setTimeout> | undefined;

    const ping = async () => {
      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          if (!cancelled) setState("ready");
          return;
        }
      } catch {
        /* network error while the instance boots */
      }
      if (cancelled) return;
      if (Date.now() - start > GIVE_UP_MS) setState("down");
      else retry = setTimeout(ping, RETRY_MS);
    };
    ping();
    return () => {
      cancelled = true;
      clearTimeout(slow);
      clearTimeout(retry);
    };
  }, [attempt]);

  if (state === "ready") return <>{children}</>;
  if (state === "checking") return null;
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-center" role="status">
      <Logo className="h-12 w-12" />
      {state === "waking" ? (
        <>
          <p className="text-lg font-medium">Waking up the server…</p>
          <p className="text-sm text-slate-500">The free host sleeps when idle. This usually takes under a minute.</p>
          <div className="h-1 w-48 overflow-hidden rounded bg-brand-100">
            <div className="h-full w-1/3 animate-pulse rounded bg-brand-600" />
          </div>
        </>
      ) : (
        <>
          <p className="text-lg font-medium">The server isn't responding.</p>
          <button
            className="rounded-md bg-brand-700 px-4 py-2 text-white hover:bg-brand-600"
            onClick={() => {
              setState("waking");
              setAttempt((a) => a + 1);
            }}
          >
            Try again
          </button>
        </>
      )}
    </div>
  );
}
