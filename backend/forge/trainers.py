from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

import optuna
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge

from backend.registry.schemas import TaskType

try:
    from xgboost import XGBClassifier, XGBRegressor
    HAS_XGB = True
except Exception:
    HAS_XGB = False

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
    HAS_LGBM = True
except Exception:
    HAS_LGBM = False


@dataclass
class Algo:
    name: str
    task_type: TaskType
    build: Callable[[Dict[str, Any]], Any]
    space: Callable[[optuna.trial.Trial], Dict[str, Any]]


def _logreg_space(t: optuna.trial.Trial) -> Dict[str, Any]:
    return {
        "C": t.suggest_float("C", 1e-3, 1e2, log=True),
        "max_iter": 500,
        "solver": "lbfgs",
        "n_jobs": -1,
    }


def _ridge_space(t: optuna.trial.Trial) -> Dict[str, Any]:
    return {"alpha": t.suggest_float("alpha", 1e-3, 1e2, log=True)}


def _rf_space(t: optuna.trial.Trial) -> Dict[str, Any]:
    return {
        "n_estimators": t.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": t.suggest_int("max_depth", 3, 20),
        "min_samples_split": t.suggest_int("min_samples_split", 2, 10),
        "n_jobs": -1,
    }


def _gb_space(t: optuna.trial.Trial) -> Dict[str, Any]:
    return {
        "n_estimators": t.suggest_int("n_estimators", 100, 400, step=50),
        "learning_rate": t.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "max_depth": t.suggest_int("max_depth", 2, 8),
    }


def _xgb_space(t: optuna.trial.Trial) -> Dict[str, Any]:
    return {
        "n_estimators": t.suggest_int("n_estimators", 100, 600, step=50),
        "learning_rate": t.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "max_depth": t.suggest_int("max_depth", 3, 10),
        "subsample": t.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": t.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_lambda": t.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "tree_method": "hist",
        "n_jobs": -1,
        "verbosity": 0,
    }


def _lgbm_space(t: optuna.trial.Trial) -> Dict[str, Any]:
    return {
        "n_estimators": t.suggest_int("n_estimators", 100, 600, step=50),
        "learning_rate": t.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "num_leaves": t.suggest_int("num_leaves", 15, 127),
        "min_child_samples": t.suggest_int("min_child_samples", 5, 60),
        "subsample": t.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": t.suggest_float("colsample_bytree", 0.6, 1.0),
        "n_jobs": -1,
        "verbosity": -1,
    }


def _algos_classification() -> List[Algo]:
    algos = [
        Algo("logreg", TaskType.CLASSIFICATION, lambda p: LogisticRegression(**p), _logreg_space),
        Algo("random_forest", TaskType.CLASSIFICATION, lambda p: RandomForestClassifier(**p), _rf_space),
        Algo("gradient_boosting", TaskType.CLASSIFICATION, lambda p: GradientBoostingClassifier(**p), _gb_space),
    ]
    if HAS_XGB:
        algos.append(Algo("xgboost", TaskType.CLASSIFICATION, lambda p: XGBClassifier(**p), _xgb_space))
    if HAS_LGBM:
        algos.append(Algo("lightgbm", TaskType.CLASSIFICATION, lambda p: LGBMClassifier(**p), _lgbm_space))
    return algos


def _algos_regression() -> List[Algo]:
    algos = [
        Algo("ridge", TaskType.REGRESSION, lambda p: Ridge(**p), _ridge_space),
        Algo("random_forest", TaskType.REGRESSION, lambda p: RandomForestRegressor(**p), _rf_space),
        Algo("gradient_boosting", TaskType.REGRESSION, lambda p: GradientBoostingRegressor(**p), _gb_space),
    ]
    if HAS_XGB:
        algos.append(Algo("xgboost", TaskType.REGRESSION, lambda p: XGBRegressor(**p), _xgb_space))
    if HAS_LGBM:
        algos.append(Algo("lightgbm", TaskType.REGRESSION, lambda p: LGBMRegressor(**p), _lgbm_space))
    return algos


def algorithms_for(task_type: TaskType) -> List[Algo]:
    if task_type == TaskType.CLASSIFICATION:
        return _algos_classification()
    return _algos_regression()


def filter_algorithms(algos: List[Algo], names: List[str] | None) -> List[Algo]:
    if not names:
        return algos
    wanted = {n.lower() for n in names}
    return [a for a in algos if a.name in wanted]
