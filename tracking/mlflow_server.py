"""Launch a local MLflow tracking server backed by SQLite + filesystem artifacts.

Usage:
    python -m tracking.mlflow_server
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.core.config import settings
from backend.core.logger import logger


def main() -> int:
    backend_uri = f"sqlite:///{(settings.DATA_DIR / 'mlflow.db').as_posix()}"
    artifact_root = (settings.DATA_DIR / "mlruns").as_posix()
    Path(artifact_root).mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "mlflow",
        "server",
        "--backend-store-uri",
        backend_uri,
        "--default-artifact-root",
        artifact_root,
        "--host",
        "0.0.0.0",
        "--port",
        "5000",
    ]
    logger.info(f"mlflow: launching with backend={backend_uri} artifacts={artifact_root}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
