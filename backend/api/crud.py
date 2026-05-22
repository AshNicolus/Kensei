from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.api.models import Dataset, Deployment, Job, Model


def create_dataset(
    db: Session,
    *,
    name: str,
    filename: str,
    path: str,
    rows: int,
    columns: int,
    size_bytes: int,
    target_candidates: List[str],
) -> Dataset:
    ds = Dataset(
        name=name,
        filename=filename,
        path=path,
        rows=rows,
        columns=columns,
        size_bytes=size_bytes,
        target_candidates=target_candidates,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def get_dataset(db: Session, dataset_id: int) -> Optional[Dataset]:
    return db.get(Dataset, dataset_id)


def list_datasets(db: Session, limit: int = 100) -> List[Dataset]:
    return list(
        db.execute(select(Dataset).order_by(desc(Dataset.created_at)).limit(limit))
        .scalars()
        .all()
    )


def create_job(
    db: Session,
    *,
    dataset_id: int,
    target: str,
    task_type: str,
    config: Dict[str, Any],
) -> Job:
    job = Job(
        dataset_id=dataset_id,
        target=target,
        task_type=task_type,
        status="pending",
        progress=0.0,
        config=config,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> Optional[Job]:
    return db.get(Job, job_id)


def list_jobs(db: Session, limit: int = 100) -> List[Job]:
    return list(
        db.execute(select(Job).order_by(desc(Job.created_at)).limit(limit))
        .scalars()
        .all()
    )


def update_job_status(
    db: Session,
    job_id: int,
    *,
    status: Optional[str] = None,
    progress: Optional[float] = None,
    message: Optional[str] = None,
    celery_task_id: Optional[str] = None,
    best_model_id: Optional[int] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
) -> Optional[Job]:
    job = db.get(Job, job_id)
    if job is None:
        return None
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if message is not None:
        job.message = message
    if celery_task_id is not None:
        job.celery_task_id = celery_task_id
    if best_model_id is not None:
        job.best_model_id = best_model_id
    if started_at is not None:
        job.started_at = started_at
    if finished_at is not None:
        job.finished_at = finished_at
    db.commit()
    db.refresh(job)
    return job


def create_model(
    db: Session,
    *,
    job_id: int,
    algorithm: str,
    task_type: str,
    metrics: Dict[str, float],
    primary_metric: str,
    primary_score: float,
    params: Dict[str, Any],
    artifact_path: str,
    feature_names: List[str],
    mlflow_run_id: Optional[str] = None,
) -> Model:
    m = Model(
        job_id=job_id,
        algorithm=algorithm,
        task_type=task_type,
        metrics=metrics,
        primary_metric=primary_metric,
        primary_score=primary_score,
        params=params,
        artifact_path=artifact_path,
        feature_names=feature_names,
        mlflow_run_id=mlflow_run_id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def get_model(db: Session, model_id: int) -> Optional[Model]:
    return db.get(Model, model_id)


def list_models_for_job(db: Session, job_id: int) -> List[Model]:
    return list(
        db.execute(
            select(Model)
            .where(Model.job_id == job_id)
            .order_by(desc(Model.primary_score))
        )
        .scalars()
        .all()
    )


def best_model_for_job(db: Session, job_id: int) -> Optional[Model]:
    models = list_models_for_job(db, job_id)
    return models[0] if models else None


def create_deployment(
    db: Session,
    *,
    model_id: int,
    slug: str,
    endpoint: str,
    api_key_hash: Optional[str],
    api_key_prefix: Optional[str],
    generated_code_path: Optional[str],
) -> Deployment:
    dep = Deployment(
        model_id=model_id,
        slug=slug,
        status="active",
        endpoint=endpoint,
        api_key_hash=api_key_hash,
        api_key_prefix=api_key_prefix,
        generated_code_path=generated_code_path,
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


def get_deployment_by_slug(db: Session, slug: str) -> Optional[Deployment]:
    return db.execute(
        select(Deployment).where(Deployment.slug == slug)
    ).scalar_one_or_none()


def list_deployments(db: Session, limit: int = 100) -> List[Deployment]:
    return list(
        db.execute(select(Deployment).order_by(desc(Deployment.created_at)).limit(limit))
        .scalars()
        .all()
    )
