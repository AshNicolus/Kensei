"""Coverage for the Phase-1.5 backend hardening pass:
- feature_importance is persisted with each candidate model
- sample datasets are seeded into a brand-new user's account
- predict route is non-blocking (async) and serves cached models
"""
from __future__ import annotations

import inspect

import pytest


def _upload(client, csv_path, headers) -> int:
    with open(csv_path, "rb") as f:
        resp = client.post(
            "/api/datasets",
            files={"file": (csv_path.name, f, "text/csv")},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_register_seeds_sample_datasets(client):
    payload = {"email": "seed-me@example.com", "password": "longpassword"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    tok = client.post("/api/auth/login", json=payload).json()["access_token"]
    listed = client.get(
        "/api/datasets", headers={"Authorization": f"Bearer {tok}"}
    ).json()
    names = {d["name"] for d in listed}
    assert any("Iris" in n or "Diabetes" in n for n in names), (
        f"expected sample datasets seeded, got {names}"
    )


def test_feature_importance_returned_on_best_model(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    resp = client.post(
        "/api/autopilot/train",
        json={"dataset_id": ds_id, "target": "target", "preset": "quick"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    best = resp.json()["best_model"]
    assert best is not None
    fi = best.get("feature_importance") or []
    assert len(fi) > 0, "expected feature_importance list from permutation importance"
    assert all("feature" in row and "importance" in row for row in fi)
    # Importances should be sorted descending
    importances = [r["importance"] for r in fi]
    assert importances == sorted(importances, reverse=True)


def test_predict_route_is_async(client):
    """The predict endpoint must be async so blocking inference goes through
    run_in_threadpool — otherwise a slow model stalls the event loop."""
    from backend.api.routers.predict import predict

    assert inspect.iscoroutinefunction(predict), (
        "predict endpoint should be async; uses run_in_threadpool for inference"
    )


def test_model_cache_reuses_loaded_artifact(client, sample_classification_csv, auth_headers):
    """Second predict to the same deployment should reuse the cached estimator."""
    from backend.api.routers import predict as predict_mod

    ds_id = _upload(client, sample_classification_csv, auth_headers)
    out = client.post(
        "/api/autopilot/train",
        json={
            "dataset_id": ds_id,
            "target": "target",
            "preset": "quick",
            "auto_deploy": True,
            "deploy_slug": "cache-check",
        },
        headers=auth_headers,
    ).json()
    api_key = out["deployment_api_key"]
    before_keys = set(predict_mod._MODEL_CACHE.keys())
    for _ in range(3):
        r = client.post(
            "/api/deployments/cache-check/predict",
            json={"rows": [{"x1": 0.1, "x2": 0.0, "x3": 0.0, "cat": "a"}]},
            headers={"X-API-Key": api_key},
        )
        assert r.status_code == 200
    after_keys = set(predict_mod._MODEL_CACHE.keys())
    # Exactly one new cache entry for this deployment's model, not three
    assert len(after_keys - before_keys) == 1
