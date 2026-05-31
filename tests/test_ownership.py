"""Cross-user isolation: user A must not see user B's data."""
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


def test_dataset_invisible_across_users(client, sample_classification_csv, auth_user, second_user):
    _, headers_a = auth_user
    _, headers_b = second_user

    ds_id_a = _upload(client, sample_classification_csv, headers_a)

    listed_b = client.get("/api/datasets", headers=headers_b).json()
    assert all(d["id"] != ds_id_a for d in listed_b)

    direct = client.get(f"/api/datasets/{ds_id_a}", headers=headers_b)
    assert direct.status_code == 404

    cols = client.get(f"/api/datasets/{ds_id_a}/columns", headers=headers_b)
    assert cols.status_code == 404


def test_cannot_train_on_other_users_dataset(client, sample_classification_csv, auth_user, second_user):
    _, headers_a = auth_user
    _, headers_b = second_user

    ds_id_a = _upload(client, sample_classification_csv, headers_a)
    resp = client.post(
        "/api/jobs",
        json={"dataset_id": ds_id_a, "target": "target", "trials": 1, "cv_folds": 2},
        headers=headers_b,
    )
    assert resp.status_code == 404


def test_job_invisible_across_users(client, sample_classification_csv, auth_user, second_user):
    _, headers_a = auth_user
    _, headers_b = second_user

    ds_id_a = _upload(client, sample_classification_csv, headers_a)
    job = client.post(
        "/api/jobs",
        json={
            "dataset_id": ds_id_a,
            "target": "target",
            "trials": 2,
            "cv_folds": 2,
            "algorithms": ["logreg"],
        },
        headers=headers_a,
    ).json()

    listed_b = client.get("/api/jobs", headers=headers_b).json()
    assert all(j["id"] != job["id"] for j in listed_b)

    direct = client.get(f"/api/jobs/{job['id']}", headers=headers_b)
    assert direct.status_code == 404

    models = client.get(f"/api/jobs/{job['id']}/models", headers=headers_b)
    assert models.status_code == 404


def test_cannot_deploy_other_users_model(client, sample_classification_csv, auth_user, second_user):
    _, headers_a = auth_user
    _, headers_b = second_user

    ds_id = _upload(client, sample_classification_csv, headers_a)
    job = client.post(
        "/api/jobs",
        json={
            "dataset_id": ds_id,
            "target": "target",
            "trials": 2,
            "cv_folds": 2,
            "algorithms": ["logreg"],
        },
        headers=headers_a,
    ).json()
    assert job["status"] == "succeeded"
    best = client.get(f"/api/jobs/{job['id']}/best", headers=headers_a).json()

    resp = client.post(
        "/api/deploy",
        json={"model_id": best["id"], "slug": "cross-user-deny"},
        headers=headers_b,
    )
    assert resp.status_code == 404


def test_deployment_list_scoped(client, sample_classification_csv, auth_user, second_user):
    _, headers_a = auth_user
    _, headers_b = second_user

    ds_id = _upload(client, sample_classification_csv, headers_a)
    job = client.post(
        "/api/jobs",
        json={
            "dataset_id": ds_id,
            "target": "target",
            "trials": 2,
            "cv_folds": 2,
            "algorithms": ["logreg"],
        },
        headers=headers_a,
    ).json()
    best = client.get(f"/api/jobs/{job['id']}/best", headers=headers_a).json()
    dep = client.post(
        "/api/deploy",
        json={"model_id": best["id"], "slug": "owner-scope"},
        headers=headers_a,
    ).json()
    slug = dep["deployment"]["slug"]

    listed_b = client.get("/api/deploy", headers=headers_b).json()
    assert all(d["slug"] != slug for d in listed_b)

    direct = client.get(f"/api/deploy/{slug}", headers=headers_b)
    assert direct.status_code == 404
