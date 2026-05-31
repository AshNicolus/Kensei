from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.registry.schemas import TaskType

MIN_TRAINING_ROWS = 20
ID_LIKE_NAMES = {"id", "_id", "uuid", "guid", "row", "index", "rownum", "row_id"}
PREFERRED_TARGET_NAMES = {
    "target", "label", "y", "class", "outcome", "saleprice", "price",
    "score", "rating", "churn", "label_", "is_fraud", "fraud", "default",
}


@dataclass
class PreparedData:
    X: pd.DataFrame
    y: pd.Series
    feature_names: List[str]
    categorical_cols: List[str]
    numeric_cols: List[str]
    task_type: TaskType
    classes_: List[str]


class DataPreparationError(ValueError):
    """Raised when input data cannot be turned into a usable training set."""


def _looks_id_like(name: str, series: pd.Series) -> bool:
    n = name.strip().lower()
    if n in ID_LIKE_NAMES or n.endswith("_id"):
        return True
    # Unique integer column → only treat as ID once we have enough rows that
    # uniqueness can't reasonably be coincidence in real training data.
    if series.dtype.kind in {"i", "u"} and series.is_unique and len(series) >= 50:
        return True
    return False


def infer_task_type(y: pd.Series) -> TaskType:
    s = y.dropna()
    if s.empty:
        return TaskType.CLASSIFICATION
    if s.dtype.kind in {"i", "u", "f"}:
        nunique = s.nunique()
        if s.dtype.kind == "f":
            return TaskType.REGRESSION
        if nunique <= max(20, int(0.05 * len(s))):
            return TaskType.CLASSIFICATION
        return TaskType.REGRESSION
    if s.dtype == bool:
        return TaskType.CLASSIFICATION
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
    min_rows: int = MIN_TRAINING_ROWS,
) -> PreparedData:
    if target not in df.columns:
        raise DataPreparationError(f"Target column '{target}' is not in the dataset.")
    if df.shape[0] == 0:
        raise DataPreparationError("Dataset is empty — no rows to train on.")

    X = df.drop(columns=[target]).copy()
    y = df[target].copy()

    # Drop columns that are uniformly missing or constant — they can't help
    constant_cols = [c for c in X.columns if X[c].nunique(dropna=True) <= 1]
    if constant_cols:
        X = X.drop(columns=constant_cols)
    # Drop ID-like columns automatically (high-cardinality unique identifiers)
    id_cols = [c for c in X.columns if _looks_id_like(c, X[c])]
    if id_cols:
        X = X.drop(columns=id_cols)

    if X.shape[1] == 0:
        raise DataPreparationError(
            "No usable feature columns remain after dropping ID and constant columns."
        )

    mask = y.notna()
    X, y = X.loc[mask], y.loc[mask]

    inferred = task_type or infer_task_type(y)
    classes_: List[str] = []
    if inferred == TaskType.CLASSIFICATION:
        y = y.astype("category")
        classes_ = [str(c) for c in y.cat.categories.tolist()]
        if len(classes_) < 2:
            raise DataPreparationError(
                f"Target '{target}' has only {len(classes_)} class — need at least 2 for classification."
            )
        y = y.cat.codes.astype(np.int64)
    else:
        y = pd.to_numeric(y, errors="coerce")
        m2 = y.notna()
        X, y = X.loc[m2], y.loc[m2].astype(float)

    if X.shape[0] < min_rows:
        raise DataPreparationError(
            f"Only {X.shape[0]} usable rows remain after preprocessing target '{target}' "
            f"(need at least {min_rows}). Check for missing values or pick a different target."
        )

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


def _sample_values(s: pd.Series, k: int = 5) -> List[Any]:
    vc = s.dropna().value_counts().head(k)
    return [
        (v.item() if hasattr(v, "item") else v) for v in vc.index.tolist()
    ]


def per_column_analysis(df: pd.DataFrame) -> List[Dict[str, Any]]:
    n = max(len(df), 1)
    out: List[Dict[str, Any]] = []
    for c in df.columns:
        s = df[c]
        missing = int(s.isna().sum())
        try:
            unique = int(s.nunique(dropna=True))
        except Exception:
            unique = -1
        out.append(
            {
                "name": c,
                "dtype": str(s.dtype),
                "missing": missing,
                "missing_pct": round(missing / n, 4),
                "unique": unique,
                "sample_values": _sample_values(s),
                "id_like": _looks_id_like(c, s),
                "constant": unique <= 1,
            }
        )
    return out


def suggest_target_candidates(df: pd.DataFrame, top_k: int = 5) -> List[str]:
    cols = list(df.columns)
    # Filter out ID-like and constant columns upfront
    eligible = [c for c in cols if not _looks_id_like(c, df[c]) and df[c].nunique(dropna=True) >= 2]
    if not eligible:
        eligible = cols

    # Explicit name preference (case-insensitive contains)
    preferred: List[str] = []
    for c in eligible:
        n = c.strip().lower()
        if n in PREFERRED_TARGET_NAMES or any(p in n for p in {"target", "label", "price", "outcome", "score"}):
            preferred.append(c)
    if preferred:
        return preferred[:top_k]

    # Heuristic: the LAST column of a CSV is often the label
    last = eligible[-1] if eligible else None

    # Otherwise score by cardinality: prefer mid-range (likely classification target)
    scored: List[Tuple[str, int, int]] = []
    n_rows = max(len(df), 1)
    for c in eligible:
        n = int(df[c].nunique(dropna=True))
        # Prefer 2..20 unique values (likely categorical target) over very high cardinality
        if 2 <= n <= max(20, int(0.05 * n_rows)):
            score = 0  # best tier
        else:
            score = 1
        scored.append((c, score, n))
    scored.sort(key=lambda x: (x[1], x[2]))
    out = [c for c, _, _ in scored[:top_k]]
    if last and last not in out:
        out = [last] + out[: top_k - 1]
    return out
