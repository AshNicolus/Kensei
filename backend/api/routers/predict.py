from __future__ import annotations

from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.api import crud
from backend.api.deps import get_db
from backend.core.security import verify_api_key
from backend.registry.manager import load_artifact
from backend.registry.schemas import PredictRequest, PredictResponse

router = APIRouter(prefix="/deployments", tags=["deployments"])


def _check_key(dep, provided_key: str | None) -> None:
    if dep.api_key_hash:
        if not verify_api_key(provided_key, dep.api_key_hash):
            raise HTTPException(status_code=401, detail="invalid API key")


@router.post("/{slug}/predict", response_model=PredictResponse)
def predict(
    slug: str,
    payload: PredictRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
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
        estimator = load_artifact(model.artifact_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to load model artifact: {e}")

    try:
        preds = estimator.predict(df).tolist()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"prediction failed: {e}")

    proba: List[List[float]] | None = None
    if model.task_type == "classification":
        inner = estimator.named_steps.get("model") if hasattr(estimator, "named_steps") else estimator
        if hasattr(inner, "predict_proba"):
            try:
                proba = estimator.predict_proba(df).tolist()
            except Exception:
                proba = None

    return PredictResponse(
        predictions=preds,
        probabilities=proba,
        model_id=model.id,
        deployment_slug=slug,
    )
