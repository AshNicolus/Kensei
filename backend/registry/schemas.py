from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeploymentStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    FAILED = "failed"


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    filename: str
    path: str
    rows: int
    columns: int
    size_bytes: int
    target_candidates: List[str] = Field(default_factory=list)
    created_at: datetime


class TrainRequest(BaseModel):
    dataset_id: int
    target: str
    task_type: Optional[TaskType] = None
    trials: int = Field(default=15, ge=1, le=200)
    cv_folds: int = Field(default=3, ge=2, le=10)
    test_size: float = Field(default=0.2, gt=0.0, lt=0.9)
    algorithms: Optional[List[str]] = None
    time_limit_seconds: Optional[int] = Field(default=None, ge=10, le=3600)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    target: str
    task_type: TaskType
    status: JobStatus
    progress: float = 0.0
    message: Optional[str] = None
    best_model_id: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    algorithm: str
    task_type: TaskType
    metrics: Dict[str, float] = Field(default_factory=dict)
    primary_metric: str
    primary_score: float
    params: Dict[str, Any] = Field(default_factory=dict)
    artifact_path: str
    feature_names: List[str] = Field(default_factory=list)
    created_at: datetime


class DeploymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    slug: str
    status: DeploymentStatus
    endpoint: str
    api_key_prefix: Optional[str] = None
    created_at: datetime


class DeployRequest(BaseModel):
    model_id: int
    slug: Optional[str] = Field(default=None, max_length=64)


class PredictRequest(BaseModel):
    rows: List[Dict[str, Any]]


class PredictResponse(BaseModel):
    predictions: List[Any]
    probabilities: Optional[List[List[float]]] = None
    model_id: int
    deployment_slug: str


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ColumnAnalysis(BaseModel):
    name: str
    dtype: str
    missing: int
    missing_pct: float
    unique: int
    sample_values: List[Any] = Field(default_factory=list)
    id_like: bool = False
    constant: bool = False


class DatasetAnalysis(BaseModel):
    dataset_id: int
    name: str
    rows: int
    columns_count: int
    columns: List[ColumnAnalysis]
    suggested_target: Optional[str] = None
    suggested_task_type: Optional[TaskType] = None
    target_candidates: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class AutopilotRequest(BaseModel):
    dataset_id: int
    target: Optional[str] = None
    preset: str = Field(default="balanced", pattern="^(quick|balanced|thorough)$")
    auto_deploy: bool = False
    deploy_slug: Optional[str] = Field(default=None, max_length=64)


class AutopilotResponse(BaseModel):
    job: JobOut
    best_model: Optional[ModelOut] = None
    deployment_slug: Optional[str] = None
    deployment_endpoint: Optional[str] = None
    deployment_api_key: Optional[str] = None
    chose_target: str
    chose_task_type: TaskType
    chose_algorithms: Optional[List[str]] = None
    chose_trials: int
    warnings: List[str] = Field(default_factory=list)
