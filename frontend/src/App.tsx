import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useMe } from "./api/auth";
import { AuthPage } from "./pages/AuthPage";
import { Home } from "./pages/Home";
import { PlanPage } from "./pages/PlanPage";

// Pages that render questions pull in KaTeX (and the exam, the calculator), so they load on demand.
const Drill = lazy(() => import("./pages/Drill").then((m) => ({ default: m.Drill })));
const ExamHome = lazy(() => import("./pages/Exam").then((m) => ({ default: m.ExamHome })));
const ExamResults = lazy(() => import("./pages/ExamResults").then((m) => ({ default: m.ExamResults })));
const ExamRunner = lazy(() => import("./pages/ExamRunner").then((m) => ({ default: m.ExamRunner })));
const Mistakes = lazy(() => import("./pages/Mistakes").then((m) => ({ default: m.Mistakes })));
const Training = lazy(() => import("./pages/Training").then((m) => ({ default: m.Training })));

function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe();
  if (me.isPending) return null;
  if (me.isError) return <p className="p-6 text-red-700">Couldn't load your session. Reload the page.</p>;
  if (!me.data) return <Navigate to="/login" replace />;
  return <Suspense fallback={<p className="p-6 text-slate-500">Loading…</p>}>{children}</Suspense>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Home />
          </RequireAuth>
        }
      />
      {[
        ["/drill", <Drill />],
        ["/exam", <ExamHome />],
        ["/exam/:id", <ExamRunner />],
        ["/exam/:id/results", <ExamResults />],
        ["/training", <Training />],
        ["/mistakes", <Mistakes />],
        ["/plan", <PlanPage />],
      ].map(([path, page]) => (
        <Route key={path as string} path={path as string} element={<RequireAuth>{page}</RequireAuth>} />
      ))}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
