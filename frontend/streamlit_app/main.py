from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
import streamlit as st

from frontend.streamlit_app import components as api

st.set_page_config(page_title="Kensei", page_icon=":crossed_swords:", layout="wide")


def _token() -> Optional[str]:
    return st.session_state.get("auth_token")


def _logout() -> None:
    for k in ("auth_token", "auth_email"):
        st.session_state.pop(k, None)


def _login_gate() -> bool:
    if _token():
        return True
    st.title(":crossed_swords: Kensei")
    st.caption("Sign in to use the AutoML platform.")

    try:
        api.health()
    except Exception as e:
        st.error(f"API unreachable: {e}")
        return False

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login", type="primary")
        if submit:
            try:
                tok = api.login(email.strip(), password)
                st.session_state["auth_token"] = tok["access_token"]
                st.session_state["auth_email"] = email.strip()
                st.rerun()
            except api.ApiError as e:
                st.error(str(e))

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("Email", key="register_email")
            name = st.text_input("Full name (optional)", key="register_name")
            password = st.text_input(
                "Password (8+ chars)", type="password", key="register_password"
            )
            submit = st.form_submit_button("Create account", type="primary")
        if submit:
            try:
                api.register(email.strip(), password, full_name=name.strip() or None)
                tok = api.login(email.strip(), password)
                st.session_state["auth_token"] = tok["access_token"]
                st.session_state["auth_email"] = email.strip()
                st.success("Account created.")
                st.rerun()
            except api.ApiError as e:
                st.error(str(e))

    return False


def _sidebar(token: str) -> str:
    st.sidebar.title(":crossed_swords: Kensei")
    st.sidebar.caption("AutoML — CSV to API")
    try:
        h = api.health()
        st.sidebar.success(f"API: {h.get('app')} v{h.get('version')}")
    except Exception as e:
        st.sidebar.error(f"API down: {e}")
    email = st.session_state.get("auth_email", "?")
    st.sidebar.markdown(f"**Signed in:** `{email}`")
    if st.sidebar.button("Logout"):
        _logout()
        st.rerun()
    return st.sidebar.radio(
        "Navigate",
        ["Upload", "Train", "Jobs", "Deploy", "Predict"],
        index=0,
    )


def _page_upload(token: str) -> None:
    st.header("Upload dataset")
    file = st.file_uploader("CSV file", type=["csv"])
    if file is not None:
        if st.button("Upload", type="primary"):
            with st.spinner("Uploading..."):
                try:
                    res = api.upload_csv(token, file.name, file.getvalue())
                    st.success(
                        f"Uploaded #{res['id']} — {res['rows']} rows × {res['columns']} cols"
                    )
                    st.json(res)
                except api.ApiError as e:
                    st.error(str(e))

    st.subheader("Your datasets")
    ds = api.list_datasets(token)
    if ds:
        st.dataframe(pd.DataFrame(ds), use_container_width=True)
    else:
        st.info("No datasets yet. Upload one above.")


def _page_train(token: str) -> None:
    st.header("Train a model")
    datasets = api.list_datasets(token)
    if not datasets:
        st.info("Upload a dataset first.")
        return

    options = {f"#{d['id']} — {d['name']} ({d['rows']}×{d['columns']})": d for d in datasets}
    label = st.selectbox("Dataset", list(options.keys()))
    ds = options[label]

    cols_info = api.dataset_columns(token, ds["id"])
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

    task_type = st.selectbox(
        "Task type (auto-detect if blank)", ["auto", "classification", "regression"]
    )
    algos_input = st.text_input(
        "Algorithms (comma-separated, blank = all)",
        placeholder="logreg, random_forest, xgboost",
    )
    time_limit = st.number_input(
        "Time limit (sec, 0 = none)", min_value=0, max_value=3600, value=0, step=30
    )

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
            job = api.create_job(token, payload)
            st.success(f"Job #{job['id']} created — {job['status']}")
            st.session_state["last_job_id"] = job["id"]
            st.json(job)
        except api.ApiError as e:
            st.error(str(e))


def _page_jobs(token: str) -> None:
    st.header("Jobs")
    jobs = api.list_jobs(token)
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
            j = api.get_job(token, int(job_id))
            slot.markdown(
                f"**Job #{j['id']}** {api.status_badge(j['status'])} — {j.get('message') or ''}"
            )
            bar.progress(min(1.0, float(j.get("progress") or 0.0)))
            if j["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(2)
        st.success("Done.")

    try:
        j = api.get_job(token, int(job_id))
        st.subheader(f"Job #{j['id']} — {api.status_badge(j['status'])}")
        st.json(j)
        models = api.list_models(token, int(job_id))
        if models:
            st.subheader("Candidates")
            st.dataframe(pd.DataFrame(models), use_container_width=True)
    except api.ApiError as e:
        st.error(str(e))


def _page_deploy(token: str) -> None:
    st.header("Deploy a model")
    jobs = [j for j in api.list_jobs(token) if j["status"] == "succeeded"]
    if not jobs:
        st.info("Need at least one succeeded job.")
        return
    job_label = {f"Job #{j['id']} — {j['target']}": j for j in jobs}
    selected = st.selectbox("Job", list(job_label.keys()))
    job = job_label[selected]
    models = api.list_models(token, job["id"])
    if not models:
        st.warning("No candidate models on this job.")
        return
    m_label = {f"{m['algorithm']} — {m['primary_metric']}={m['primary_score']:.4f}": m for m in models}
    chosen = st.selectbox("Model", list(m_label.keys()))
    model = m_label[chosen]
    slug = st.text_input("Slug (optional)", placeholder=f"my-model-{model['id']}")

    if st.button("Deploy", type="primary"):
        try:
            res = api.deploy(token, model["id"], slug or None)
            st.success(f"Deployed at {res['deployment']['endpoint']}")
            st.warning(f"API key (shown once): `{res['api_key']}`")
            st.json(res)
        except api.ApiError as e:
            st.error(str(e))

    st.subheader("Your deployments")
    deps = api.list_deployments(token)
    if deps:
        st.dataframe(pd.DataFrame(deps), use_container_width=True)


def _page_predict(token: str) -> None:
    st.header("Predict")
    deps = api.list_deployments(token)
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
    if not _login_gate():
        return
    token = _token()
    assert token is not None
    page = _sidebar(token)
    if page == "Upload":
        _page_upload(token)
    elif page == "Train":
        _page_train(token)
    elif page == "Jobs":
        _page_jobs(token)
    elif page == "Deploy":
        _page_deploy(token)
    elif page == "Predict":
        _page_predict(token)


if __name__ == "__main__":
    main()
else:
    main()
