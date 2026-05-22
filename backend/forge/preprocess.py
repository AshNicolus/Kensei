from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.registry.schemas import TaskType


@dataclass
class PreparedData:
    X: pd.DataFrame
    y: pd.Series
    feature_names: List[str]
    categorical_cols: List[str]
    numeric_cols: List[str]
    task_type: TaskType
    classes_: List[str]


def infer_task_type(y: pd.Series) -> TaskType:
    if y.dtype.kind in {"i", "u", "f"}:
        nunique = y.nunique(dropna=True)
        if y.dtype.kind == "f":
            return TaskType.REGRESSION
        if nunique <= max(20, int(0.05 * len(y))):
            return TaskType.CLASSIFICATION
        return TaskType.REGRESSION
    return TaskType.CLASSIFICATION


def split_feature_types(X: pd.DataFrame) -> Tuple[List[str], List[str]]:
    numeric_cols = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [c for c in X.columns if c not in numeric_cols]
    return numeric_cols, categorical_cols


def build_preprocessor(numeric_cols: List[str], categorical_cols: List[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=1),
            ),
        ]
    )
    transformers = []
    if numeric_cols:
        transformers.append(("num", numeric_pipe, numeric_cols))
    if categorical_cols:
        transformers.append(("cat", categorical_pipe, categorical_cols))
    return ColumnTransformer(transformers=transformers, remainder="drop", verbose_feature_names_out=False)


def prepare(
    df: pd.DataFrame,
    target: str,
    task_type: TaskType | None = None,
) -> PreparedData:
    if target not in df.columns:
        raise ValueError(f"target '{target}' not in columns")
    X = df.drop(columns=[target]).copy()
    y = df[target].copy()
    mask = y.notna()
    X, y = X.loc[mask], y.loc[mask]

    inferred = task_type or infer_task_type(y)
    classes_: List[str] = []
    if inferred == TaskType.CLASSIFICATION:
        y = y.astype("category")
        classes_ = [str(c) for c in y.cat.categories.tolist()]
        y = y.cat.codes.astype(np.int64)
    else:
        y = pd.to_numeric(y, errors="coerce")
        m2 = y.notna()
        X, y = X.loc[m2], y.loc[m2].astype(float)

    numeric_cols, categorical_cols = split_feature_types(X)
    return PreparedData(
        X=X,
        y=y,
        feature_names=list(X.columns),
        categorical_cols=categorical_cols,
        numeric_cols=numeric_cols,
        task_type=inferred,
        classes_=classes_,
    )


def load_dataframe(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def summarize_dataset(df: pd.DataFrame) -> dict:
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "missing": {c: int(df[c].isna().sum()) for c in df.columns},
    }


def suggest_target_candidates(df: pd.DataFrame, top_k: int = 5) -> List[str]:
    preferred = [c for c in df.columns if c.lower() in {"target", "label", "y", "class", "outcome"}]
    if preferred:
        return preferred[:top_k]
    scored = []
    for c in df.columns:
        n = df[c].nunique(dropna=True)
        if n < 2:
            continue
        scored.append((c, n))
    scored.sort(key=lambda x: x[1])
    return [c for c, _ in scored[:top_k]]
