from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api import crud
from backend.api.deps import get_db
from backend.core.logger import logger
from backend.deployment.generator import generate
from backend.registry.schemas import DeployRequest, DeploymentOut

router = APIRouter(prefix="/deploy", tags=["deploy"])


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def deploy_model(req: DeployRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    model = crud.get_model(db, req.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")

    gen = generate(
        model_id=model.id,
        slug=req.slug,
        algorithm=model.algorithm,
        task_type=model.task_type,
        feature_names=model.feature_names or [],
        artifact_path=model.artifact_path,
        create_api_key=True,
    )

    if crud.get_deployment_by_slug(db, gen.slug) is not None:
        raise HTTPException(status_code=409, detail=f"deployment slug '{gen.slug}' already exists")

    dep = crud.create_deployment(
        db,
        model_id=model.id,
        slug=gen.slug,
        endpoint=gen.endpoint,
        api_key_hash=gen.api_key_hash,
        api_key_prefix=gen.api_key_prefix,
        generated_code_path=str(gen.output_dir),
    )
    logger.info(f"deploy: created deployment {dep.slug} -> {dep.endpoint}")
    return {
        "deployment": DeploymentOut.model_validate(dep).model_dump(mode="json"),
        "api_key": gen.api_key_plain,
        "generated_dir": str(gen.output_dir),
        "warning": "store the api_key now; it will not be shown again",
    }


@router.get("", response_model=List[DeploymentOut])
def list_deployments(db: Session = Depends(get_db)) -> List[DeploymentOut]:
    return [DeploymentOut.model_validate(d) for d in crud.list_deployments(db)]


@router.get("/{slug}", response_model=DeploymentOut)
def get_deployment(slug: str, db: Session = Depends(get_db)) -> DeploymentOut:
    dep = crud.get_deployment_by_slug(db, slug)
    if dep is None:
        raise HTTPException(status_code=404, detail="deployment not found")
    return DeploymentOut.model_validate(dep)
