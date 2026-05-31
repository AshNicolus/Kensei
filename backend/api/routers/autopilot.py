"""High-level convenience endpoints: analyze a dataset, train with smart
defaults, optionally deploy in one call.

Everything here scopes to the current user via Depends(get_current_user).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api import crud
from backend.api.auth import get_current_user
from backend.api.deps import get_db
from backend.api.models import User
from backend.core.logger import logger
from backend.deployment.generator import generate
from backend.forge.pipeline import smart_defaults
from backend.forge.preprocess import (
    DataPreparationError,
    infer_task_type,
    load_dataframe,
    per_column_analysis,
    suggest_target_candidates,
)
from backend.registry.schemas import (
    AutopilotRequest,
    AutopilotResponse,
    ColumnAnalysis,
    DatasetAnalysis,
    DeploymentOut,
    JobOut,
    ModelOut,
    TaskType,
)

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


@router.get("/analyze/{dataset_id}", response_model=DatasetAnalysis)
def analyze_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DatasetAnalysis:
    ds = crud.get_dataset(db, dataset_id, owner_id=user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    try:
        df = load_dataframe(ds.path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read dataset: {e}")

    cols = per_column_analysis(df)
    candidates = suggest_target_candidates(df)
    chosen_target = candidates[0] if candidates else None
    suggested_task: Optional[TaskType] = None
    warnings: List[str] = []

    if chosen_target is not None:
        try:
            suggested_task = infer_task_type(df[chosen_target])
        except Exception:
            warnings.append(f"Could not infer task type for '{chosen_target}'.")

    if df.shape[0] < 50:
        warnings.append("Dataset is small (<50 rows); training quality will be limited.")
    high_missing = [c["name"] for c in cols if c["missing_pct"] > 0.5]
    if high_missing:
        warnings.append(
            f"Columns with >50% missing values: {', '.join(high_missing[:5])}"
            + ("…" if len(high_missing) > 5 else "")
        )

    return DatasetAnalysis(
        dataset_id=ds.id,
        name=ds.name,
        rows=int(df.shape[0]),
        columns_count=int(df.shape[1]),
        columns=[ColumnAnalysis(**c) for c in cols],
        suggested_target=chosen_target,
        suggested_task_type=suggested_task,
        target_candidates=candidates,
        warnings=warnings,
    )


_PRESET_TRIAL_CAP = {"quick": 6, "balanced": 20, "thorough": 60}
_PRESET_CV_CAP = {"quick": 2, "balanced": 4, "thorough": 5}


def _resolve_preset(preset: str, rows: int, cols: int, task_type: TaskType) -> dict:
    sd = smart_defaults(rows, cols, task_type)
    trials = min(sd["trials"], _PRESET_TRIAL_CAP.get(preset, sd["trials"]))
    cv_folds = min(sd["cv_folds"], _PRESET_CV_CAP.get(preset, sd["cv_folds"]))
    if preset == "quick":
        algos = sd["algorithms"] or (["logreg", "random_forest"] if task_type == TaskType.CLASSIFICATION else ["ridge", "random_forest"])
    elif preset == "thorough":
        algos = sd["algorithms"]
    else:
        algos = sd["algorithms"]
    return {"trials": trials, "cv_folds": cv_folds, "algorithms": algos}


@router.post("/train", response_model=AutopilotResponse, status_code=status.HTTP_201_CREATED)
def autopilot_train(
    req: AutopilotRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AutopilotResponse:
    ds = crud.get_dataset(db, req.dataset_id, owner_id=user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="dataset not found")

    try:
        df = load_dataframe(ds.path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read dataset: {e}")

    warnings: List[str] = []

    target = req.target
    if target is None:
        candidates = suggest_target_candidates(df)
        if not candidates:
            raise HTTPException(status_code=400, detail="no target column could be suggested")
        target = candidates[0]
        warnings.append(f"Target not provided; chose '{target}' automatically.")
    elif target not in df.columns:
        raise HTTPException(status_code=400, detail=f"target '{target}' not in dataset")

    try:
        task_type = infer_task_type(df[target])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"could not infer task type: {e}")

    defaults = _resolve_preset(req.preset, df.shape[0], df.shape[1], task_type)
    config = {
        "trials": defaults["trials"],
        "cv_folds": defaults["cv_folds"],
        "test_size": 0.2,
        "algorithms": defaults["algorithms"],
        "time_limit_seconds": None,
        "preset": req.preset,
    }

    job = crud.create_job(
        db,
        owner_id=user.id,
        dataset_id=ds.id,
        target=target,
        task_type=task_type.value,
        config=config,
    )
    logger.info(
        f"autopilot: job={job.id} owner={user.id} dataset={ds.id} target={target} "
        f"task={task_type.value} preset={req.preset}"
    )

    try:
        from backend.workers.tasks import train_job as train_task

        train_task.apply(args=[job.id])
    except Exception as e:
        logger.exception("autopilot: training run failed")
        crud.update_job_status(db, job.id, status="failed", message=str(e)[:1000])

    db.refresh(job)

    best = crud.best_model_for_job(db, job.id, owner_id=user.id)
    best_out = ModelOut.model_validate(best) if best else None

    deployment_slug: Optional[str] = None
    deployment_endpoint: Optional[str] = None
    deployment_api_key: Optional[str] = None

    if req.auto_deploy and best is not None and job.status == "succeeded":
        gen = generate(
            model_id=best.id,
            slug=req.deploy_slug,
            algorithm=best.algorithm,
            task_type=best.task_type,
            feature_names=best.feature_names or [],
            artifact_path=best.artifact_path,
            create_api_key=True,
        )
        if crud.get_deployment_by_slug(db, gen.slug) is not None:
            warnings.append(f"Deployment slug '{gen.slug}' already taken; skipping auto-deploy.")
        else:
            dep = crud.create_deployment(
                db,
                owner_id=user.id,
                model_id=best.id,
                slug=gen.slug,
                endpoint=gen.endpoint,
                api_key_hash=gen.api_key_hash,
                api_key_prefix=gen.api_key_prefix,
                generated_code_path=str(gen.output_dir),
            )
            deployment_slug = dep.slug
            deployment_endpoint = dep.endpoint
            deployment_api_key = gen.api_key_plain

    return AutopilotResponse(
        job=JobOut.model_validate(job),
        best_model=best_out,
        deployment_slug=deployment_slug,
        deployment_endpoint=deployment_endpoint,
        deployment_api_key=deployment_api_key,
        chose_target=target,
        chose_task_type=task_type,
        chose_algorithms=defaults["algorithms"],
        chose_trials=defaults["trials"],
        warnings=warnings,
    )
