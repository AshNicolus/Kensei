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


def test_analyze_returns_columns_and_suggestion(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    resp = client.get(f"/api/autopilot/analyze/{ds_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dataset_id"] == ds_id
    assert body["rows"] > 0
    assert body["columns_count"] > 0
    col_names = [c["name"] for c in body["columns"]]
    assert "target" in col_names
    assert "cat" in col_names
    assert body["suggested_target"] in col_names
    cat_col = next(c for c in body["columns"] if c["name"] == "cat")
    assert cat_col["unique"] >= 2
    assert cat_col["sample_values"]


def test_analyze_invisible_across_users(client, sample_classification_csv, auth_user, second_user):
    _, headers_a = auth_user
    _, headers_b = second_user
    ds_id = _upload(client, sample_classification_csv, headers_a)
    resp = client.get(f"/api/autopilot/analyze/{ds_id}", headers=headers_b)
    assert resp.status_code == 404


def test_autopilot_train_picks_target_and_succeeds(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    resp = client.post(
        "/api/autopilot/train",
        json={"dataset_id": ds_id, "preset": "quick"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["job"]["status"] == "succeeded", body["job"]
    assert body["best_model"] is not None
    assert body["chose_target"]
    assert body["chose_task_type"] in {"classification", "regression"}
    assert body["chose_trials"] <= 8


def test_autopilot_train_with_auto_deploy(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    resp = client.post(
        "/api/autopilot/train",
        json={
            "dataset_id": ds_id,
            "target": "target",
            "preset": "quick",
            "auto_deploy": True,
            "deploy_slug": "autopilot-smoke",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["deployment_slug"] == "autopilot-smoke"
    assert body["deployment_api_key"]

    pred = client.post(
        "/api/deployments/autopilot-smoke/predict",
        json={"rows": [{"x1": 0.1, "x2": -0.2, "x3": 0.0, "cat": "a"}]},
        headers={"X-API-Key": body["deployment_api_key"]},
    )
    assert pred.status_code == 200, pred.text
    assert len(pred.json()["predictions"]) == 1


def test_autopilot_rejects_unknown_target(client, sample_classification_csv, auth_headers):
    ds_id = _upload(client, sample_classification_csv, auth_headers)
    resp = client.post(
        "/api/autopilot/train",
        json={"dataset_id": ds_id, "target": "no_such_column"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_empty_data_after_target_yields_clear_error(client, tmp_path, auth_headers):
    import pandas as pd

    # Target column is entirely empty -> after dropna, zero usable rows
    df = pd.DataFrame({"x1": [1, 2, 3], "x2": [4, 5, 6], "target": [None, None, None]})
    p = tmp_path / "bad.csv"
    df.to_csv(p, index=False)
    ds_id = _upload(client, p, auth_headers)
    resp = client.post(
        "/api/jobs",
        json={
            "dataset_id": ds_id,
            "target": "target",
            "trials": 2,
            "cv_folds": 2,
            "algorithms": ["logreg"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    job = resp.json()
    assert job["status"] == "failed"
    assert "rows" in (job.get("message") or "").lower() or "target" in (job.get("message") or "").lower()
