from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

_TEST_DIR = Path(tempfile.mkdtemp(prefix="kensei_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'kensei_test.db').as_posix()}"
os.environ["ENV"] = "test"
os.environ["MLFLOW_TRACKING_URI"] = f"file:{(_TEST_DIR / 'mlruns').as_posix()}"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"

from backend.core.config import settings  # noqa: E402

settings.DATA_DIR = _TEST_DIR
settings.UPLOADS_DIR = _TEST_DIR / "uploads"
settings.MODELS_DIR = _TEST_DIR / "models"
settings.ARTIFACTS_DIR = _TEST_DIR / "artifacts"
settings.ensure_dirs()

from backend.workers.celery_app import celery_app  # noqa: E402

celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True


@pytest.fixture(scope="session")
def test_dir() -> Path:
    return _TEST_DIR


@pytest.fixture()
def sample_classification_csv(tmp_path: Path) -> Path:
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame(
        {
            "x1": rng.normal(size=n),
            "x2": rng.normal(size=n),
            "x3": rng.normal(size=n),
            "cat": rng.choice(["a", "b", "c"], size=n),
        }
    )
    logits = 1.2 * df["x1"] - 0.7 * df["x2"] + (df["cat"] == "a").astype(float)
    df["target"] = (logits + rng.normal(scale=0.4, size=n) > 0).astype(int)
    path = tmp_path / "classif.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture()
def sample_regression_csv(tmp_path: Path) -> Path:
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(1)
    n = 200
    df = pd.DataFrame(
        {
            "x1": rng.normal(size=n),
            "x2": rng.normal(size=n),
            "x3": rng.normal(size=n),
        }
    )
    df["target"] = 2.0 * df["x1"] - 1.5 * df["x2"] + 0.3 * df["x3"] + rng.normal(scale=0.2, size=n)
    path = tmp_path / "reg.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture()
def client() -> Iterator:
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as c:
        yield c
