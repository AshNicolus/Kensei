from __future__ import annotations

import io
import json
import time
from typing import Any, Dict

import pandas as pd
import streamlit as st

from frontend.streamlit_app import components as api

st.set_page_config(page_title="Kensei", page_icon=":crossed_swords:", layout="wide")


def _sidebar() -> str:
    st.sidebar.title(":crossed_swords: Kensei")
    st.sidebar.caption("AutoML — CSV to API")
    try:
        h = api.health()
        st.sidebar.success(f"API: {h.get('app')} v{h.get('version')}")
    except Exception as e:
        st.sidebar.error(f"API down: {e}")
    return st.sidebar.radio(
        "Navigate",
        ["Upload", "Train", "Jobs", "Deploy", "Predict"],
        index=0,
    )


def _page_upload() -> None:
    st.header("Upload dataset")
    file = st.file_uploader("CSV file", type=["csv"])
    if file is not None:
        if st.button("Upload", type="primary"):
            with st.spinner("Uploading..."):
                try:
                    res = api.upload_csv(file.name, file.getvalue())
                    st.success(
                        f"Uploaded #{res['id']} — {res['rows']} rows × {res['columns']} cols"
                    )
                    st.json(res)
                except api.ApiError as e:
                    st.error(str(e))

    st.subheader("Existing datasets")
    ds = api.list_datasets()
    if ds:
        st.dataframe(pd.DataFrame(ds), use_container_width=True)
    else:
        st.info("No datasets yet. Upload one above.")


def _page_train() -> None:
    st.header("Train a model")
    datasets = api.list_datasets()
    if not datasets:
        st.info("Upload a dataset first.")
        return

    options = {f"#{d['id']} — {d['name']} ({d['rows']}×{d['columns']})": d for d in datasets}
    label = st.selectbox("Dataset", list(options.keys()))
    ds = options[label]

    cols_info = api.dataset_columns(ds["id"])
    target_candidates = cols_info.get("target_candidates") or cols_info["columns"]
    target = st.selectbox(
        "Target column",
        cols_info["columns"],
        index=cols_info["columns"].index(target_candidates[0]) if target_candidates else 0,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        trials = st.slider("Optuna trials / algo", 3, 60, 15)
    with c2:
        cv_folds = st.slider("CV folds", 2, 10, 3)
    with c3:
        test_size = st.slider("Test size", 0.1, 0.5, 0.2, step=0.05)

    task_type = st.selectbox("Task type (auto-detect if blank)", ["auto", "classification", "regression"])
    algos_input = st.text_input(
        "Algorithms (comma-separated, blank = all)",
        placeholder="logreg, random_forest, xgboost",
    )
    time_limit = st.number_input("Time limit (sec, 0 = none)", min_value=0, max_value=3600, value=0, step=30)

    if st.button("Launch training", type="primary"):
        payload: Dict[str, Any] = {
            "dataset_id": ds["id"],
            "target": target,
            "trials": trials,
            "cv_folds": cv_folds,
            "test_size": test_size,
        }
        if task_type != "auto":
            payload["task_type"] = task_type
        algos = [a.strip() for a in algos_input.split(",") if a.strip()]
        if algos:
            payload["algorithms"] = algos
        if time_limit > 0:
            payload["time_limit_seconds"] = int(time_limit)
        try:
            job = api.create_job(payload)
            st.success(f"Job #{job['id']} created — {job['status']}")
            st.session_state["last_job_id"] = job["id"]
            st.json(job)
        except api.ApiError as e:
            st.error(str(e))


def _page_jobs() -> None:
    st.header("Jobs")
    jobs = api.list_jobs()
    if not jobs:
        st.info("No jobs yet.")
        return
    df = pd.DataFrame(jobs)
    st.dataframe(df, use_container_width=True)

    job_id = st.number_input("Job id to inspect", min_value=1, value=int(df["id"].iloc[0]))
    if st.button("Refresh"):
        st.rerun()
    if st.button("Auto-poll until done"):
        slot = st.empty()
        bar = st.progress(0.0)
        while True:
            j = api.get_job(int(job_id))
            slot.markdown(
                f"**Job #{j['id']}** {api.status_badge(j['status'])} — {j.get('message') or ''}"
            )
            bar.progress(min(1.0, float(j.get("progress") or 0.0)))
            if j["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(2)
        st.success("Done.")

    try:
        j = api.get_job(int(job_id))
        st.subheader(f"Job #{j['id']} — {api.status_badge(j['status'])}")
        st.json(j)
        models = api.list_models(int(job_id))
        if models:
            st.subheader("Candidates")
            st.dataframe(pd.DataFrame(models), use_container_width=True)
    except api.ApiError as e:
        st.error(str(e))


def _page_deploy() -> None:
    st.header("Deploy a model")
    jobs = [j for j in api.list_jobs() if j["status"] == "succeeded"]
    if not jobs:
        st.info("Need at least one succeeded job.")
        return
    job_label = {f"Job #{j['id']} — {j['target']}": j for j in jobs}
    selected = st.selectbox("Job", list(job_label.keys()))
    job = job_label[selected]
    models = api.list_models(job["id"])
    if not models:
        st.warning("No candidate models on this job.")
        return
    m_label = {f"{m['algorithm']} — {m['primary_metric']}={m['primary_score']:.4f}": m for m in models}
    chosen = st.selectbox("Model", list(m_label.keys()))
    model = m_label[chosen]
    slug = st.text_input("Slug (optional)", placeholder=f"my-model-{model['id']}")

    if st.button("Deploy", type="primary"):
        try:
            res = api.deploy(model["id"], slug or None)
            st.success(f"Deployed at {res['deployment']['endpoint']}")
            st.warning(f"API key (shown once): `{res['api_key']}`")
            st.json(res)
        except api.ApiError as e:
            st.error(str(e))

    st.subheader("Deployments")
    deps = api.list_deployments()
    if deps:
        st.dataframe(pd.DataFrame(deps), use_container_width=True)


def _page_predict() -> None:
    st.header("Predict")
    deps = api.list_deployments()
    if not deps:
        st.info("No deployments yet.")
        return
    dep_label = {f"{d['slug']} (model #{d['model_id']})": d for d in deps}
    chosen = st.selectbox("Deployment", list(dep_label.keys()))
    dep = dep_label[chosen]
    api_key = st.text_input("API key", type="password")

    mode = st.radio("Input mode", ["JSON rows", "CSV upload"], horizontal=True)
    rows: list = []
    if mode == "JSON rows":
        default = json.dumps([{"feature_1": 0, "feature_2": 0}], indent=2)
        text = st.text_area("Rows as JSON array", value=default, height=200)
        try:
            rows = json.loads(text)
            if not isinstance(rows, list):
                st.error("JSON must be an array of objects.")
                rows = []
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
    else:
        up = st.file_uploader("CSV with feature rows", type=["csv"], key="predict_csv")
        if up is not None:
            df = pd.read_csv(io.BytesIO(up.getvalue()))
            st.dataframe(df.head(), use_container_width=True)
            rows = df.to_dict(orient="records")

    if rows and st.button("Run prediction", type="primary"):
        try:
            res = api.predict(dep["slug"], rows, api_key=api_key or None)
            st.success("Done")
            st.json(res)
        except api.ApiError as e:
            st.error(str(e))


def main() -> None:
    page = _sidebar()
    if page == "Upload":
        _page_upload()
    elif page == "Train":
        _page_train()
    elif page == "Jobs":
        _page_jobs()
    elif page == "Deploy":
        _page_deploy()
    elif page == "Predict":
        _page_predict()


if __name__ == "__main__":
    main()
else:
    main()
