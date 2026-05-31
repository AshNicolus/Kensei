from __future__ import annotations

import asyncio
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.api import crud
from backend.api.deps import SessionLocal, get_db
from backend.core.logger import logger
from backend.core.security import verify_api_key
from backend.registry.manager import load_artifact
from backend.registry.schemas import PredictRequest, PredictResponse

router = APIRouter(prefix="/deployments", tags=["deployments"])

# Process-local model cache: load each artifact once, reuse across requests.
# Keyed by (model_id, artifact_path) so artifact swaps are detected.
_MODEL_CACHE: Dict[Tuple[int, str], Any] = {}
_CACHE_LOCK = Lock()


def _get_estimator(model_id: int, artifact_path: str):
    key = (model_id, artifact_path)
    with _CACHE_LOCK:
        cached = _MODEL_CACHE.get(key)
    if cached is not None:
        return cached
    estimator = load_artifact(artifact_path)
    with _CACHE_LOCK:
        _MODEL_CACHE[key] = estimator
    return estimator


def warmup_deployments() -> None:
    """Preload every active deployment's model + run a no-op predict so the
    first real user call doesn't pay the 10-50x lazy-init tax."""
    db = SessionLocal()
    try:
        deployments = crud.list_active_deployments(db)
        for dep in deployments:
            model = crud.get_model(db, dep.model_id)
            if model is None:
                continue
            try:
                est = _get_estimator(model.id, model.artifact_path)
                if model.feature_names:
                    df = pd.DataFrame(
                        [{c: 0 for c in model.feature_names}]
                    )[model.feature_names]
                    est.predict(df)
                logger.info(
                    f"warmup: preloaded model id={model.id} slug={dep.slug}"
                )
            except Exception as e:
                logger.warning(f"warmup: failed for slug={dep.slug}: {e}")
    finally:
        db.close()


def _check_key(dep, provided_key: Optional[str]) -> None:
    if dep.api_key_hash:
        if not verify_api_key(provided_key, dep.api_key_hash):
            raise HTTPException(status_code=401, detail="invalid API key")


def _run_predict_sync(
    estimator,
    df: pd.DataFrame,
    task_type: str,
) -> Tuple[List[Any], Optional[List[List[float]]]]:
    preds = estimator.predict(df).tolist()
    proba: Optional[List[List[float]]] = None
    if task_type == "classification":
        inner = estimator.named_steps.get("model") if hasattr(estimator, "named_steps") else estimator
        if hasattr(inner, "predict_proba"):
            try:
                proba = estimator.predict_proba(df).tolist()
            except Exception:
                proba = None
    return preds, proba


@router.post("/{slug}/predict", response_model=PredictResponse)
async def predict(
    slug: str,
    payload: PredictRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> PredictResponse:
    dep = crud.get_deployment_by_slug(db, slug)
    if dep is None or dep.status != "active":
        raise HTTPException(status_code=404, detail="deployment not found or inactive")
    _check_key(dep, x_api_key)

    model = crud.get_model(db, dep.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="backing model missing")

    if not payload.rows:
        raise HTTPException(status_code=400, detail="rows must be non-empty")

    df = pd.DataFrame(payload.rows)
    for col in model.feature_names or []:
        if col not in df.columns:
            df[col] = None
    if model.feature_names:
        df = df[model.feature_names]

    try:
        estimator = await run_in_threadpool(_get_estimator, model.id, model.artifact_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to load model artifact: {e}")

    try:
        preds, proba = await run_in_threadpool(
            _run_predict_sync, estimator, df, model.task_type
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"prediction failed: {e}")

    return PredictResponse(
        predictions=preds,
        probabilities=proba,
        model_id=model.id,
        deployment_slug=slug,
    )
