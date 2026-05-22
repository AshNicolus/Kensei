from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery import shared_task

from backend.api import crud
from backend.api.deps import SessionLocal
from backend.core.logger import logger
from backend.forge import pipeline as forge_pipeline
from backend.forge.preprocess import load_dataframe
from backend.registry import manager as registry_manager
from backend.registry.schemas import JobStatus, TaskType
from backend.workers.celery_app import celery_app


def _now() -> datetime:
    return datetime.now(timezone.utc)


@shared_task(bind=True, name="kensei.train_job")
def train_job(self, job_id: int) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        job = crud.get_job(db, job_id)
        if job is None:
            raise RuntimeError(f"job {job_id} not found")

        crud.update_job_status(
            db,
            job_id,
            status=JobStatus.RUNNING.value,
            progress=0.01,
            message="loading dataset",
            celery_task_id=self.request.id,
            started_at=_now(),
        )

        ds = crud.get_dataset(db, job.dataset_id)
        if ds is None:
            raise RuntimeError(f"dataset {job.dataset_id} not found")

        df = load_dataframe(ds.path)

        cfg = job.config or {}
        algorithms = cfg.get("algorithms")
        trials = int(cfg.get("trials", 15))
        cv_folds = int(cfg.get("cv_folds", 3))
        test_size = float(cfg.get("test_size", 0.2))
        time_limit = cfg.get("time_limit_seconds")
        task_hint: Optional[TaskType] = TaskType(job.task_type) if job.task_type else None

        def _progress(p: float, msg: str) -> None:
            try:
                with SessionLocal() as db2:
                    crud.update_job_status(db2, job_id, progress=min(0.99, max(0.0, p)), message=msg)
            except Exception:
                logger.exception("failed to write progress")

        result = forge_pipeline.run_training(
            df=df,
            target=job.target,
            task_type_hint=task_hint,
            algorithms=algorithms,
            trials=trials,
            cv_folds=cv_folds,
            test_size=test_size,
            time_limit_seconds=time_limit,
            progress_cb=_progress,
        )

        best_model_id: Optional[int] = None
        for fitted in result.candidates:
            run_id = registry_manager.log_to_mlflow(
                fitted, job_id=job_id, dataset_name=ds.name
            )
            artifact = registry_manager.save_artifact(job_id, fitted, mlflow_run_id=run_id)
            m = crud.create_model(
                db,
                job_id=job_id,
                algorithm=fitted.algorithm,
                task_type=fitted.task_type.value,
                metrics=fitted.metrics,
                primary_metric=fitted.primary_metric,
                primary_score=fitted.primary_score,
                params=fitted.params,
                artifact_path=str(artifact.model_path),
                feature_names=fitted.feature_names,
                mlflow_run_id=run_id,
            )
            if fitted.algorithm == result.best.algorithm and best_model_id is None:
                best_model_id = m.id

        crud.update_job_status(
            db,
            job_id,
            status=JobStatus.SUCCEEDED.value,
            progress=1.0,
            message=f"best={result.best.algorithm} score={result.best.primary_score:.4f}",
            best_model_id=best_model_id,
            finished_at=_now(),
        )
        return {
            "job_id": job_id,
            "best_algorithm": result.best.algorithm,
            "primary_metric": result.best.primary_metric,
            "primary_score": result.best.primary_score,
            "n_candidates": len(result.candidates),
        }
    except Exception as e:
        logger.exception(f"train_job failed for job {job_id}")
        try:
            with SessionLocal() as db2:
                crud.update_job_status(
                    db2,
                    job_id,
                    status=JobStatus.FAILED.value,
                    message=str(e)[:1000],
                    finished_at=_now(),
                )
        except Exception:
            pass
        raise
    finally:
        db.close()


celery_app.tasks.register(train_job)
