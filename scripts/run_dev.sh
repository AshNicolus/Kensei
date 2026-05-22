#!/usr/bin/env bash
# Kensei dev launcher — starts API, Celery worker, MLflow tracking, and Streamlit.
# Requires Redis running locally on :6379 (or set REDIS_URL).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"
export ENV="${ENV:-development}"

mkdir -p data/uploads data/models data/artifacts data/mlruns

echo "[kensei] init db"
python -m scripts.init_db

LOG_DIR="$ROOT_DIR/data/logs"
mkdir -p "$LOG_DIR"

echo "[kensei] starting MLflow at :5000"
mlflow server \
  --backend-store-uri "sqlite:///$ROOT_DIR/data/mlflow.db" \
  --default-artifact-root "$ROOT_DIR/data/mlruns" \
  --host 0.0.0.0 --port 5000 \
  > "$LOG_DIR/mlflow.log" 2>&1 &
MLFLOW_PID=$!

echo "[kensei] starting Celery worker"
celery -A backend.workers.celery_app worker --loglevel=info \
  > "$LOG_DIR/celery.log" 2>&1 &
CELERY_PID=$!

echo "[kensei] starting FastAPI at :8000"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload \
  > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!

echo "[kensei] starting Streamlit at :8501"
streamlit run frontend/streamlit_app/main.py \
  --server.port 8501 --server.address 0.0.0.0 \
  > "$LOG_DIR/streamlit.log" 2>&1 &
ST_PID=$!

cleanup() {
  echo "[kensei] stopping..."
  kill $ST_PID $API_PID $CELERY_PID $MLFLOW_PID 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[kensei] up. API=:8000  Streamlit=:8501  MLflow=:5000"
echo "[kensei] tailing logs (Ctrl-C to stop)"
tail -n +1 -F "$LOG_DIR/api.log" "$LOG_DIR/celery.log" "$LOG_DIR/streamlit.log" "$LOG_DIR/mlflow.log"
