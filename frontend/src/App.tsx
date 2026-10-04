import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useMe } from "./api/auth";
import { AuthPage } from "./pages/AuthPage";
import { Drill } from "./pages/Drill";
import { ExamHome } from "./pages/Exam";
import { ExamResults } from "./pages/ExamResults";
import { ExamRunner } from "./pages/ExamRunner";
import { Home } from "./pages/Home";
import { Mistakes } from "./pages/Mistakes";
import { Training } from "./pages/Training";

function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe();
  if (me.isPending) return null;
  if (me.isError) return <p className="p-6 text-red-700">Couldn't load your session. Reload the page.</p>;
  return me.data ? <>{children}</> : <Navigate to="/login" replace />;
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
      ].map(([path, page]) => (
        <Route key={path as string} path={path as string} element={<RequireAuth>{page}</RequireAuth>} />
      ))}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
