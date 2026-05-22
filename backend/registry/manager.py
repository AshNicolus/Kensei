from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import cloudpickle

from backend.core.config import settings
from backend.core.logger import logger
from backend.forge.pipeline import FittedModel
from backend.registry.schemas import TaskType


@dataclass
class StoredArtifact:
    model_path: Path
    meta_path: Path
    feature_names: List[str]
    task_type: TaskType
    primary_metric: str
    primary_score: float
    metrics: Dict[str, float]
    params: Dict[str, Any]
    algorithm: str
    mlflow_run_id: Optional[str]


def _artifact_dir(job_id: int, model_tag: str) -> Path:
    out = settings.MODELS_DIR / f"job_{job_id}" / model_tag
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_artifact(job_id: int, fitted: FittedModel, mlflow_run_id: Optional[str] = None) -> StoredArtifact:
    out = _artifact_dir(job_id, fitted.algorithm)
    model_path = out / "model.pkl"
    meta_path = out / "meta.json"
    with model_path.open("wb") as f:
        cloudpickle.dump(fitted.estimator, f)
    meta: Dict[str, Any] = {
        "algorithm": fitted.algorithm,
        "task_type": fitted.task_type.value,
        "primary_metric": fitted.primary_metric,
        "primary_score": fitted.primary_score,
        "metrics": fitted.metrics,
        "params": fitted.params,
        "feature_names": fitted.feature_names,
        "mlflow_run_id": mlflow_run_id,
    }
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    logger.info(f"registry: saved artifact for job={job_id} algo={fitted.algorithm} -> {model_path}")
    return StoredArtifact(
        model_path=model_path,
        meta_path=meta_path,
        feature_names=fitted.feature_names,
        task_type=fitted.task_type,
        primary_metric=fitted.primary_metric,
        primary_score=fitted.primary_score,
        metrics=fitted.metrics,
        params=fitted.params,
        algorithm=fitted.algorithm,
        mlflow_run_id=mlflow_run_id,
    )


def load_artifact(path: str | Path):
    p = Path(path)
    with p.open("rb") as f:
        return cloudpickle.load(f)


def load_meta(meta_path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(meta_path).read_text(encoding="utf-8"))


def log_to_mlflow(
    fitted: FittedModel,
    job_id: int,
    dataset_name: str,
    extra_tags: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    try:
        import mlflow
    except Exception as e:
        logger.warning(f"registry: mlflow unavailable ({e}); skipping logging")
        return None
    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT)
        with mlflow.start_run(run_name=f"job_{job_id}_{fitted.algorithm}") as run:
            mlflow.set_tag("kensei.job_id", str(job_id))
            mlflow.set_tag("kensei.dataset", dataset_name)
            mlflow.set_tag("kensei.algorithm", fitted.algorithm)
            mlflow.set_tag("kensei.task_type", fitted.task_type.value)
            for k, v in (extra_tags or {}).items():
                mlflow.set_tag(k, v)
            mlflow.log_params({k: str(v) for k, v in fitted.params.items()})
            mlflow.log_metrics({k: float(v) for k, v in fitted.metrics.items() if isinstance(v, (int, float))})
            return run.info.run_id
    except Exception as e:
        logger.warning(f"registry: mlflow logging failed: {e}")
        return None
