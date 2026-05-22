from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
