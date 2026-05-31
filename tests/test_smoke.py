"""End-to-end smoke test: register → upload → train → deploy → predict.

Runs entirely in-process: Celery is configured in eager mode in conftest,
SQLite + filesystem artifacts under a temp dir, no external broker required.
"""
from __future__ import annotations


def _upload(client, csv_path, headers) -> int:
    with open(csv_path, "rb") as f:
        resp = client.post(
            "/api/datasets",
            files={"file": (csv_path.name, f, "text/csv")},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "Kensei"


def test_upload_lists_dataset(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    resp = client.get(f"/api/datasets/{ds_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["rows"] > 0
    assert body["columns"] > 0


def test_dataset_columns_endpoint(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    resp = client.get(f"/api/datasets/{ds_id}/columns", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "columns" in body
    assert "target" in body["columns"]


def test_end_to_end_classification(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)

    resp = client.post(
        "/api/jobs",
        json={
            "dataset_id": ds_id,
            "target": "target",
            "trials": 3,
            "cv_folds": 2,
            "test_size": 0.25,
            "algorithms": ["logreg"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    job = resp.json()
    job_id = job["id"]

    resp = client.get(f"/api/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    job = resp.json()
    assert job["status"] == "succeeded", f"job failed: {job}"
    assert job["best_model_id"] is not None

    resp = client.get(f"/api/jobs/{job_id}/best", headers=auth_headers)
    assert resp.status_code == 200
    best = resp.json()
    assert best["algorithm"] == "logreg"
    assert "f1_macro" in best["metrics"]

    resp = client.post(
        "/api/deploy",
        json={"model_id": best["id"], "slug": "smoke-test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    deploy_body = resp.json()
    assert deploy_body["deployment"]["slug"] == "smoke-test"
    api_key = deploy_body["api_key"]
    assert api_key

    rows = [{"x1": 0.5, "x2": -0.2, "x3": 0.1, "cat": "a"}]
    resp = client.post(
        "/api/deployments/smoke-test/predict",
        json={"rows": rows},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200, resp.text
    pred = resp.json()
    assert len(pred["predictions"]) == 1
    assert pred["deployment_slug"] == "smoke-test"


def test_predict_rejects_bad_api_key(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    job_resp = client.post(
        "/api/jobs",
        json={
            "dataset_id": ds_id,
            "target": "target",
            "trials": 2,
            "cv_folds": 2,
            "test_size": 0.25,
            "algorithms": ["logreg"],
        },
        headers=auth_headers,
    )
    assert job_resp.status_code == 201
    job = job_resp.json()
    assert job["status"] == "succeeded"

    best = client.get(f"/api/jobs/{job['id']}/best", headers=auth_headers).json()
    dep_resp = client.post(
        "/api/deploy",
        json={"model_id": best["id"], "slug": "auth-test"},
        headers=auth_headers,
    )
    assert dep_resp.status_code == 201

    bad = client.post(
        "/api/deployments/auth-test/predict",
        json={"rows": [{"x1": 0, "x2": 0, "x3": 0, "cat": "a"}]},
        headers={"X-API-Key": "wrong-key"},
    )
    assert bad.status_code == 401


def test_train_unknown_dataset_returns_404(client, auth_headers):
    resp = client.post(
        "/api/jobs",
        json={"dataset_id": 99999, "target": "target", "trials": 1, "cv_folds": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 404
