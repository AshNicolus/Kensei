from __future__ import annotations

import pandas as pd
import pytest

from backend.forge import pipeline, preprocess
from backend.registry.schemas import TaskType


def test_infer_task_type_classification():
    y = pd.Series([0, 1, 0, 1, 1, 0])
    assert preprocess.infer_task_type(y) == TaskType.CLASSIFICATION


def test_infer_task_type_regression():
    y = pd.Series([1.1, 2.3, 4.5, 6.7, 8.9, 10.1, 12.3])
    assert preprocess.infer_task_type(y) == TaskType.REGRESSION


def test_prepare_splits_feature_types(sample_classification_csv):
    df = pd.read_csv(sample_classification_csv)
    prepared = preprocess.prepare(df, target="target")
    assert prepared.task_type == TaskType.CLASSIFICATION
    assert "cat" in prepared.categorical_cols
    assert {"x1", "x2", "x3"}.issubset(set(prepared.numeric_cols))
    assert "target" not in prepared.feature_names


def test_run_training_classification(sample_classification_csv):
    df = pd.read_csv(sample_classification_csv)
    result = pipeline.run_training(
        df,
        target="target",
        algorithms=["logreg"],
        trials=3,
        cv_folds=2,
        test_size=0.25,
    )
    assert result.best.algorithm == "logreg"
    assert result.best.task_type == TaskType.CLASSIFICATION
    assert "f1_macro" in result.best.metrics
    assert result.best.primary_score >= 0.0


def test_run_training_regression(sample_regression_csv):
    df = pd.read_csv(sample_regression_csv)
    result = pipeline.run_training(
        df,
        target="target",
        algorithms=["ridge"],
        trials=3,
        cv_folds=2,
        test_size=0.25,
    )
    assert result.best.algorithm == "ridge"
    assert result.best.task_type == TaskType.REGRESSION
    assert result.best.primary_score > 0.8


def test_run_training_unknown_algo_raises(sample_classification_csv):
    df = pd.read_csv(sample_classification_csv)
    with pytest.raises(ValueError):
        pipeline.run_training(
            df,
            target="target",
            algorithms=["does_not_exist"],
            trials=1,
            cv_folds=2,
        )
