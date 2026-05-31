"""Bundled sample datasets seeded into a new user's account so the UI is
never empty on first visit. Keep these small + deterministic — they exist
to support a 60-second 'try it' loop, not to be benchmarks.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.api import crud
from backend.api.models import User
from backend.core.config import settings
from backend.core.logger import logger
from backend.forge.preprocess import load_dataframe, suggest_target_candidates


def _iris_df() -> pd.DataFrame:
    try:
        from sklearn.datasets import load_iris

        data = load_iris(as_frame=True)
        df: pd.DataFrame = data.frame
        df = df.rename(columns={"target": "species"})
        df["species"] = df["species"].map(dict(enumerate(data.target_names)))
        return df
    except Exception:
        # Tiny manual fallback if sklearn is unavailable in this env.
        rng = np.random.default_rng(42)
        return pd.DataFrame(
            {
                "sepal_length": rng.normal(5.5, 0.8, 60),
                "sepal_width": rng.normal(3.0, 0.4, 60),
                "petal_length": rng.normal(3.7, 1.5, 60),
                "petal_width": rng.normal(1.2, 0.7, 60),
                "species": (["setosa"] * 20 + ["versicolor"] * 20 + ["virginica"] * 20),
            }
        )


def _diabetes_df() -> pd.DataFrame:
    try:
        from sklearn.datasets import load_diabetes

        data = load_diabetes(as_frame=True)
        df: pd.DataFrame = data.frame
        return df
    except Exception:
        rng = np.random.default_rng(0)
        n = 150
        x = rng.normal(size=(n, 4))
        y = 2.0 * x[:, 0] - 1.5 * x[:, 1] + 0.3 * x[:, 2] + rng.normal(scale=0.2, size=n)
        return pd.DataFrame(
            {
                "age": x[:, 0],
                "bmi": x[:, 1],
                "bp": x[:, 2],
                "s1": x[:, 3],
                "target": y,
            }
        )


def _persist_sample(db: Session, user: User, df: pd.DataFrame, name: str) -> None:
    settings.ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    safe = name.lower().replace(" ", "_")
    dest = settings.UPLOADS_DIR / f"u{user.id}_{ts}_sample_{safe}.csv"
    df.to_csv(dest, index=False)
    candidates = suggest_target_candidates(df)
    crud.create_dataset(
        db,
        owner_id=user.id,
        name=name,
        filename=dest.name,
        path=str(dest),
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        size_bytes=dest.stat().st_size,
        target_candidates=candidates,
    )


def seed_samples_for_user(db: Session, user: User) -> List[str]:
    """Idempotent-ish: seeds two sample datasets the first time a user has none.
    Returns the names of seeded datasets (empty list if user already had data).
    """
    existing = crud.list_datasets(db, owner_id=user.id, limit=1)
    if existing:
        return []
    seeded: List[str] = []
    try:
        _persist_sample(db, user, _iris_df(), "Iris (sample)")
        seeded.append("Iris (sample)")
    except Exception as e:
        logger.warning(f"sample seed iris failed: {e}")
    try:
        _persist_sample(db, user, _diabetes_df(), "Diabetes (sample)")
        seeded.append("Diabetes (sample)")
    except Exception as e:
        logger.warning(f"sample seed diabetes failed: {e}")
    if seeded:
        logger.info(f"seeded {len(seeded)} sample dataset(s) for user id={user.id}")
    return seeded
