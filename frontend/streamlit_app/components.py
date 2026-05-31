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


def _bearer(token: Optional[str]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


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


def register(email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    return _raise_for(
        requests.post(
            _url("/api/auth/register"),
            json={"email": email, "password": password, "full_name": full_name},
            timeout=TIMEOUT,
        )
    )


def login(email: str, password: str) -> Dict[str, Any]:
    return _raise_for(
        requests.post(
            _url("/api/auth/login"),
            json={"email": email, "password": password},
            timeout=TIMEOUT,
        )
    )


def me(token: str) -> Dict[str, Any]:
    return _raise_for(
        requests.get(_url("/api/auth/me"), headers=_bearer(token), timeout=TIMEOUT)
    )


def upload_csv(token: str, filename: str, content: bytes) -> Dict[str, Any]:
    files = {"file": (filename, content, "text/csv")}
    return _raise_for(
        requests.post(_url("/api/datasets"), files=files, headers=_bearer(token), timeout=TIMEOUT)
    )


def list_datasets(token: str) -> List[Dict[str, Any]]:
    return _raise_for(
        requests.get(_url("/api/datasets"), headers=_bearer(token), timeout=TIMEOUT)
    ) or []


def dataset_columns(token: str, dataset_id: int) -> Dict[str, Any]:
    return _raise_for(
        requests.get(
            _url(f"/api/datasets/{dataset_id}/columns"),
            headers=_bearer(token),
            timeout=TIMEOUT,
        )
    )


def create_job(token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _raise_for(
        requests.post(_url("/api/jobs"), json=payload, headers=_bearer(token), timeout=TIMEOUT)
    )


def list_jobs(token: str) -> List[Dict[str, Any]]:
    return _raise_for(
        requests.get(_url("/api/jobs"), headers=_bearer(token), timeout=TIMEOUT)
    ) or []


def get_job(token: str, job_id: int) -> Dict[str, Any]:
    return _raise_for(
        requests.get(_url(f"/api/jobs/{job_id}"), headers=_bearer(token), timeout=TIMEOUT)
    )


def list_models(token: str, job_id: int) -> List[Dict[str, Any]]:
    return _raise_for(
        requests.get(_url(f"/api/jobs/{job_id}/models"), headers=_bearer(token), timeout=TIMEOUT)
    ) or []


def best_model(token: str, job_id: int) -> Optional[Dict[str, Any]]:
    return _raise_for(
        requests.get(_url(f"/api/jobs/{job_id}/best"), headers=_bearer(token), timeout=TIMEOUT)
    )


def deploy(token: str, model_id: int, slug: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"model_id": model_id}
    if slug:
        payload["slug"] = slug
    return _raise_for(
        requests.post(_url("/api/deploy"), json=payload, headers=_bearer(token), timeout=TIMEOUT)
    )


def list_deployments(token: str) -> List[Dict[str, Any]]:
    return _raise_for(
        requests.get(_url("/api/deploy"), headers=_bearer(token), timeout=TIMEOUT)
    ) or []


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
