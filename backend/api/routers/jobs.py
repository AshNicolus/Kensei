from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api import crud
from backend.api.auth import get_current_user
from backend.api.deps import get_db
from backend.api.models import User
from backend.core.logger import logger
from backend.forge.preprocess import infer_task_type, load_dataframe
from backend.registry.schemas import (
    JobOut,
    ModelOut,
    TaskType,
    TrainRequest,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _resolve_task_type(req: TrainRequest, dataset_path: str) -> TaskType:
    if req.task_type is not None:
        return req.task_type
    try:
        df = load_dataframe(dataset_path)
        if req.target not in df.columns:
            raise HTTPException(status_code=400, detail=f"target '{req.target}' not in dataset")
        return infer_task_type(df[req.target])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to infer task type: {e}")


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    req: TrainRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    ds = crud.get_dataset(db, req.dataset_id, owner_id=user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="dataset not found")

    task_type = _resolve_task_type(req, ds.path)
    config = {
        "trials": req.trials,
        "cv_folds": req.cv_folds,
        "test_size": req.test_size,
        "algorithms": req.algorithms,
        "time_limit_seconds": req.time_limit_seconds,
    }
    job = crud.create_job(
        db,
        owner_id=user.id,
        dataset_id=req.dataset_id,
        target=req.target,
        task_type=task_type.value,
        config=config,
    )
    logger.info(
        f"jobs: created job id={job.id} owner={user.id} dataset={req.dataset_id} task={task_type.value}"
    )

    try:
        from backend.workers.tasks import train_job as train_task

        async_result = train_task.delay(job.id)
        crud.update_job_status(db, job.id, celery_task_id=async_result.id)
    except Exception as e:
        logger.warning(f"jobs: celery dispatch failed ({e}); attempting inline fallback")
        try:
            from backend.workers.tasks import train_job as train_task

            train_task.apply(args=[job.id])
        except Exception as ee:
            logger.exception("jobs: inline training fallback also failed")
            crud.update_job_status(db, job.id, status="failed", message=f"dispatch failed: {ee}")

    db.refresh(job)
    return JobOut.model_validate(job)


@router.get("", response_model=List[JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[JobOut]:
    return [JobOut.model_validate(j) for j in crud.list_jobs(db, owner_id=user.id)]


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    job = crud.get_job(db, job_id, owner_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobOut.model_validate(job)


@router.get("/{job_id}/models", response_model=List[ModelOut])
def list_models(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[ModelOut]:
    job = crud.get_job(db, job_id, owner_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return [
        ModelOut.model_validate(m)
        for m in crud.list_models_for_job(db, job_id, owner_id=user.id)
    ]


@router.get("/{job_id}/best", response_model=Optional[ModelOut])
def best_model(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Optional[ModelOut]:
    job = crud.get_job(db, job_id, owner_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    best = crud.best_model_for_job(db, job_id, owner_id=user.id)
    return ModelOut.model_validate(best) if best else None
