from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.api import crud
from backend.api.auth import get_current_user
from backend.api.deps import get_db
from backend.api.models import User
from backend.core.config import settings
from backend.core.logger import logger
from backend.forge.preprocess import load_dataframe, suggest_target_candidates
from backend.registry.schemas import DatasetOut

router = APIRouter(prefix="/datasets", tags=["datasets"])

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    base = Path(name).name
    base = _SAFE_NAME.sub("_", base)
    return base or "upload.csv"


def _validate_extension(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_UPLOAD_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported extension '{ext}'. allowed: {settings.ALLOWED_UPLOAD_EXT}",
        )


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DatasetOut:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="missing filename")
    _validate_extension(file.filename)

    safe_name = _safe_filename(file.filename)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    dest = settings.UPLOADS_DIR / f"u{user.id}_{ts}_{safe_name}"
    dest.parent.mkdir(parents=True, exist_ok=True)

    size_bytes = 0
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    with dest.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"file exceeds max size {settings.MAX_UPLOAD_MB} MB",
                )
            out.write(chunk)

    try:
        df = load_dataframe(str(dest))
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"failed to parse CSV: {e}")

    candidates: List[str] = suggest_target_candidates(df)
    ds = crud.create_dataset(
        db,
        owner_id=user.id,
        name=Path(safe_name).stem,
        filename=safe_name,
        path=str(dest),
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        size_bytes=size_bytes,
        target_candidates=candidates,
    )
    logger.info(
        f"upload: stored dataset id={ds.id} owner={user.id} rows={ds.rows} cols={ds.columns}"
    )
    return DatasetOut.model_validate(ds)


@router.get("", response_model=List[DatasetOut])
def list_uploaded(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[DatasetOut]:
    return [DatasetOut.model_validate(d) for d in crud.list_datasets(db, owner_id=user.id)]


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DatasetOut:
    ds = crud.get_dataset(db, dataset_id, owner_id=user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    return DatasetOut.model_validate(ds)


@router.get("/{dataset_id}/columns")
def dataset_columns(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ds = crud.get_dataset(db, dataset_id, owner_id=user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    try:
        df = load_dataframe(ds.path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read dataset: {e}")
    return {
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "target_candidates": ds.target_candidates or [],
        "rows": int(df.shape[0]),
    }
