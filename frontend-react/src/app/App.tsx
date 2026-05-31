import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/shared/hooks/use-auth";
import { AppShell } from "@/shared/components/layout/AppShell";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { AutopilotPage } from "@/modules/automl/pages/AutopilotPage";
import { DatasetsPage } from "@/modules/automl/pages/DatasetsPage";
import { JobsPage } from "@/modules/automl/pages/JobsPage";
import { JobDetailPage } from "@/modules/automl/pages/JobDetailPage";
import { DeploymentsPage } from "@/modules/automl/pages/DeploymentsPage";
import { PredictPage } from "@/modules/automl/pages/PredictPage";
import { ComingSoon } from "@/shared/components/layout/ComingSoon";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<Navigate to="/automl/autopilot" replace />} />
        <Route path="automl">
          <Route index element={<Navigate to="autopilot" replace />} />
          <Route path="autopilot" element={<AutopilotPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="jobs/:jobId" element={<JobDetailPage />} />
          <Route path="deployments" element={<DeploymentsPage />} />
          <Route path="predict" element={<PredictPage />} />
        </Route>
        <Route
          path="pretraining"
          element={
            <ComingSoon
              title="Pretraining"
              tagline="Train foundation models on your own data."
            />
          }
        />
        <Route
          path="finetuning"
          element={
            <ComingSoon
              title="Fine-tuning"
              tagline="Adapt open-source LLMs to your domain."
            />
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
