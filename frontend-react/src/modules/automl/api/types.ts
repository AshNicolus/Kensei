export type TaskType = "classification" | "regression";

export type JobStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface Dataset {
  id: number;
  name: string;
  filename: string;
  path: string;
  rows: number;
  columns: number;
  size_bytes: number;
  target_candidates: string[];
  created_at: string;
}

export interface ColumnAnalysis {
  name: string;
  dtype: string;
  missing: number;
  missing_pct: number;
  unique: number;
  sample_values: unknown[];
  id_like: boolean;
  constant: boolean;
}

export interface DatasetAnalysis {
  dataset_id: number;
  name: string;
  rows: number;
  columns_count: number;
  columns: ColumnAnalysis[];
  suggested_target: string | null;
  suggested_task_type: TaskType | null;
  target_candidates: string[];
  warnings: string[];
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export interface Job {
  id: number;
  dataset_id: number;
  target: string;
  task_type: TaskType;
  status: JobStatus;
  progress: number;
  message: string | null;
  best_model_id: number | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface ModelOut {
  id: number;
  job_id: number;
  algorithm: string;
  task_type: TaskType;
  metrics: Record<string, number>;
  primary_metric: string;
  primary_score: number;
  params: Record<string, unknown>;
  artifact_path: string;
  feature_names: string[];
  feature_importance: FeatureImportance[];
  created_at: string;
}

export interface Deployment {
  id: number;
  model_id: number;
  slug: string;
  status: "active" | "inactive" | "failed";
  endpoint: string;
  api_key_prefix: string | null;
  created_at: string;
}

export type Preset = "quick" | "balanced" | "thorough";

export interface AutopilotRequest {
  dataset_id: number;
  target?: string | null;
  preset: Preset;
  auto_deploy?: boolean;
  deploy_slug?: string | null;
}

export interface AutopilotResponse {
  job: Job;
  best_model: ModelOut | null;
  deployment_slug: string | null;
  deployment_endpoint: string | null;
  deployment_api_key: string | null;
  chose_target: string;
  chose_task_type: TaskType;
  chose_algorithms: string[] | null;
  chose_trials: number;
  warnings: string[];
}

export interface PredictResponse {
  predictions: unknown[];
  probabilities: number[][] | null;
  model_id: number;
  deployment_slug: string;
}

export interface UserOut {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}
