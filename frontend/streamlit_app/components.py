from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")
TIMEOUT = 60


class ApiError(Exception):
    pass


def _url(path: str) -> str:
    return f"{API_URL.rstrip('/')}{path}"


def _raise_for(resp: requests.Response) -> Any:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        raise ApiError(f"{resp.status_code}: {detail}")
    if resp.content:
        try:
            return resp.json()
        except Exception:
            return resp.text
    return None


def health() -> Dict[str, Any]:
    return _raise_for(requests.get(_url("/health"), timeout=TIMEOUT))


def upload_csv(filename: str, content: bytes) -> Dict[str, Any]:
    files = {"file": (filename, content, "text/csv")}
    return _raise_for(requests.post(_url("/api/datasets"), files=files, timeout=TIMEOUT))


def list_datasets() -> List[Dict[str, Any]]:
    return _raise_for(requests.get(_url("/api/datasets"), timeout=TIMEOUT)) or []


def dataset_columns(dataset_id: int) -> Dict[str, Any]:
    return _raise_for(requests.get(_url(f"/api/datasets/{dataset_id}/columns"), timeout=TIMEOUT))


def create_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _raise_for(requests.post(_url("/api/jobs"), json=payload, timeout=TIMEOUT))


def list_jobs() -> List[Dict[str, Any]]:
    return _raise_for(requests.get(_url("/api/jobs"), timeout=TIMEOUT)) or []


def get_job(job_id: int) -> Dict[str, Any]:
    return _raise_for(requests.get(_url(f"/api/jobs/{job_id}"), timeout=TIMEOUT))


def list_models(job_id: int) -> List[Dict[str, Any]]:
    return _raise_for(requests.get(_url(f"/api/jobs/{job_id}/models"), timeout=TIMEOUT)) or []


def best_model(job_id: int) -> Optional[Dict[str, Any]]:
    return _raise_for(requests.get(_url(f"/api/jobs/{job_id}/best"), timeout=TIMEOUT))


def deploy(model_id: int, slug: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"model_id": model_id}
    if slug:
        payload["slug"] = slug
    return _raise_for(requests.post(_url("/api/deploy"), json=payload, timeout=TIMEOUT))


def list_deployments() -> List[Dict[str, Any]]:
    return _raise_for(requests.get(_url("/api/deploy"), timeout=TIMEOUT)) or []


def predict(slug: str, rows: List[Dict[str, Any]], api_key: Optional[str] = None) -> Dict[str, Any]:
    headers: Dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    return _raise_for(
        requests.post(
            _url(f"/api/deployments/{slug}/predict"),
            json={"rows": rows},
            headers=headers,
            timeout=TIMEOUT,
        )
    )


STATUS_COLOR = {
    "pending": "gray",
    "running": "orange",
    "succeeded": "green",
    "failed": "red",
    "cancelled": "gray",
}


def status_badge(status: str) -> str:
    color = STATUS_COLOR.get(status, "gray")
    return f":{color}[{status}]"
