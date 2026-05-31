from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import optuna
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline as SkPipeline

from backend.core.config import settings
from backend.core.logger import logger
from backend.forge import evaluate as ev
from backend.forge import preprocess as pp
from backend.forge.trainers import Algo, algorithms_for, filter_algorithms
from backend.registry.schemas import TaskType


@dataclass
class TrialResult:
    algorithm: str
    params: Dict[str, Any]
    cv_score: float


@dataclass
class FittedModel:
    algorithm: str
    task_type: TaskType
    estimator: SkPipeline
    params: Dict[str, Any]
    metrics: Dict[str, float]
    primary_metric: str
    primary_score: float
    feature_names: List[str]


@dataclass
class TrainResult:
    best: FittedModel
    candidates: List[FittedModel] = field(default_factory=list)
    trials: List[TrialResult] = field(default_factory=list)


ProgressCb = Optional[Callable[[float, str], None]]


def _cv_scorer(task_type: TaskType) -> str:
    return "f1_macro" if task_type == TaskType.CLASSIFICATION else "r2"


def _cv_splitter(task_type: TaskType, n_splits: int, seed: int):
    if task_type == TaskType.CLASSIFICATION:
        return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return KFold(n_splits=n_splits, shuffle=True, random_state=seed)


def _tune_one(
    algo: Algo,
    X,
    y,
    preprocessor,
    task_type: TaskType,
    n_trials: int,
    cv_folds: int,
    seed: int,
    time_budget_s: Optional[float],
) -> TrialResult:
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    scorer = _cv_scorer(task_type)
    splitter = _cv_splitter(task_type, cv_folds, seed)

    def objective(trial: optuna.trial.Trial) -> float:
        params = algo.space(trial)
        try:
            est = algo.build(params)
        except Exception as e:
            raise optuna.TrialPruned(str(e))
        pipe = SkPipeline([("pre", preprocessor), ("model", est)])
        scores = cross_val_score(pipe, X, y, cv=splitter, scoring=scorer, n_jobs=1, error_score="raise")
        return float(np.mean(scores))

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=time_budget_s,
        show_progress_bar=False,
        gc_after_trial=True,
    )
    return TrialResult(
        algorithm=algo.name,
        params=study.best_params,
        cv_score=float(study.best_value),
    )


def _fit_final(
    algo: Algo,
    params: Dict[str, Any],
    X_train,
    y_train,
    X_test,
    y_test,
    preprocessor,
    task_type: TaskType,
    feature_names: List[str],
) -> FittedModel:
    pipe = SkPipeline([("pre", preprocessor), ("model", algo.build(params))])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    if task_type == TaskType.CLASSIFICATION:
        proba = None
        if hasattr(pipe.named_steps["model"], "predict_proba"):
            try:
                proba = pipe.predict_proba(X_test)
            except Exception:
                proba = None
        metrics = ev.classification_metrics(np.asarray(y_test), np.asarray(y_pred), proba)
    else:
        metrics = ev.regression_metrics(
            np.asarray(y_test, dtype=float), np.asarray(y_pred, dtype=float)
        )
    primary = ev.primary_metric_for(task_type)
    return FittedModel(
        algorithm=algo.name,
        task_type=task_type,
        estimator=pipe,
        params=params,
        metrics=metrics,
        primary_metric=primary,
        primary_score=float(metrics.get(primary, 0.0)),
        feature_names=feature_names,
    )


def smart_defaults(rows: int, cols: int, task_type: TaskType) -> dict:
    """Pick reasonable Optuna trials / CV / algos based on dataset shape."""
    if rows < 200:
        trials, cv_folds = 8, 2
    elif rows < 2000:
        trials, cv_folds = 15, 3
    elif rows < 20000:
        trials, cv_folds = 20, 3
    else:
        trials, cv_folds = 10, 3
    if rows > 50000:
        algos = ["lightgbm"] if cols < 200 else ["lightgbm", "xgboost"]
    elif rows > 10000:
        algos = ["random_forest", "xgboost", "lightgbm"]
    else:
        algos = None  # full sweep
    return {"trials": trials, "cv_folds": cv_folds, "algorithms": algos}


def run_training(
    df,
    target: str,
    task_type_hint: Optional[TaskType] = None,
    algorithms: Optional[List[str]] = None,
    trials: int = 15,
    cv_folds: int = 3,
    test_size: float = 0.2,
    time_limit_seconds: Optional[int] = None,
    progress_cb: ProgressCb = None,
    seed: Optional[int] = None,
) -> TrainResult:
    seed = seed if seed is not None else settings.RANDOM_STATE
    prepared = pp.prepare(df, target=target, task_type=task_type_hint)
    preprocessor = pp.build_preprocessor(prepared.numeric_cols, prepared.categorical_cols)

    stratify = prepared.y if prepared.task_type == TaskType.CLASSIFICATION else None
    # Guard: train_test_split with too few rows produces opaque errors
    if prepared.X.shape[0] < max(int(1 / max(test_size, 0.01)), cv_folds + 1):
        from backend.forge.preprocess import DataPreparationError

        raise DataPreparationError(
            f"Only {prepared.X.shape[0]} usable rows after preprocessing — "
            f"need more for a {test_size:.0%} train/test split with {cv_folds}-fold CV."
        )
    X_train, X_test, y_train, y_test = train_test_split(
        prepared.X, prepared.y, test_size=test_size, random_state=seed, stratify=stratify
    )

    algos = filter_algorithms(algorithms_for(prepared.task_type), algorithms)
    if not algos:
        raise ValueError("no algorithms available after filtering")

    total = len(algos)
    per_algo_budget = (time_limit_seconds / total) if time_limit_seconds else None
    trial_results: List[TrialResult] = []
    candidates: List[FittedModel] = []

    started = time.time()
    for idx, algo in enumerate(algos):
        if progress_cb:
            progress_cb((idx / max(total, 1)) * 0.9, f"tuning {algo.name}")
        logger.info(f"forge: tuning {algo.name} ({idx + 1}/{total})")
        try:
            tr = _tune_one(
                algo=algo,
                X=X_train,
                y=y_train,
                preprocessor=preprocessor,
                task_type=prepared.task_type,
                n_trials=trials,
                cv_folds=cv_folds,
                seed=seed,
                time_budget_s=per_algo_budget,
            )
            trial_results.append(tr)
            fitted = _fit_final(
                algo=algo,
                params=tr.params,
                X_train=X_train,
                y_train=y_train,
                X_test=X_test,
                y_test=y_test,
                preprocessor=preprocessor,
                task_type=prepared.task_type,
                feature_names=prepared.feature_names,
            )
            candidates.append(fitted)
            logger.info(
                f"forge: {algo.name} primary={fitted.primary_score:.4f} metrics={fitted.metrics}"
            )
        except Exception as e:
            logger.warning(f"forge: {algo.name} failed: {e}")
            continue

    if not candidates:
        raise RuntimeError("all algorithms failed during training")

    candidates.sort(key=lambda c: c.primary_score, reverse=True)
    best = candidates[0]
    if progress_cb:
        elapsed = time.time() - started
        progress_cb(1.0, f"done in {elapsed:.1f}s, best={best.algorithm}")
    return TrainResult(best=best, candidates=candidates, trials=trial_results)
