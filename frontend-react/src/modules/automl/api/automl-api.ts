import { api } from "@/shared/lib/api";
import type {
  AutopilotRequest,
  AutopilotResponse,
  Dataset,
  DatasetAnalysis,
  Deployment,
  Job,
  ModelOut,
  PredictResponse,
  TokenResponse,
  UserOut,
} from "./types";

export const authApi = {
  register: (body: {
    email: string;
    password: string;
    full_name?: string | null;
  }) => api.post<UserOut>("/api/auth/register", body).then((r) => r.data),
  login: (body: { email: string; password: string }) =>
    api.post<TokenResponse>("/api/auth/login", body).then((r) => r.data),
  me: () => api.get<UserOut>("/api/auth/me").then((r) => r.data),
};

export const datasetsApi = {
  list: () => api.get<Dataset[]>("/api/datasets").then((r) => r.data),
  get: (id: number) =>
    api.get<Dataset>(`/api/datasets/${id}`).then((r) => r.data),
  upload: (file: File, onProgress?: (n: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    return api
      .post<Dataset>("/api/datasets", fd, {
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(e.loaded / e.total);
        },
      })
      .then((r) => r.data);
  },
};

export const autopilotApi = {
  analyze: (id: number) =>
    api
      .get<DatasetAnalysis>(`/api/autopilot/analyze/${id}`)
      .then((r) => r.data),
  train: (req: AutopilotRequest) =>
    api.post<AutopilotResponse>("/api/autopilot/train", req).then((r) => r.data),
};

export const jobsApi = {
  list: () => api.get<Job[]>("/api/jobs").then((r) => r.data),
  get: (id: number) => api.get<Job>(`/api/jobs/${id}`).then((r) => r.data),
  models: (id: number) =>
    api.get<ModelOut[]>(`/api/jobs/${id}/models`).then((r) => r.data),
  best: (id: number) =>
    api.get<ModelOut | null>(`/api/jobs/${id}/best`).then((r) => r.data),
};

export const deploymentsApi = {
  list: () => api.get<Deployment[]>("/api/deploy").then((r) => r.data),
  get: (slug: string) =>
    api.get<Deployment>(`/api/deploy/${slug}`).then((r) => r.data),
  predict: (slug: string, rows: Record<string, unknown>[], apiKey?: string) =>
    api
      .post<PredictResponse>(
        `/api/deployments/${slug}/predict`,
        { rows },
        apiKey ? { headers: { "X-API-Key": apiKey } } : undefined
      )
      .then((r) => r.data),
};
