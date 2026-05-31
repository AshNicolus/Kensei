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
    for k in ("auth_token", "auth_email", "active_dataset", "active_analysis", "last_autopilot"):
        st.session_state.pop(k, None)


def _login_gate() -> bool:
    if _token():
        return True
    st.title(":crossed_swords: Kensei")
    st.caption("AutoML in one click — upload a CSV, get a deployed model.")

    try:
        api.health()
    except Exception as e:
        st.error(f"Backend is not reachable: {e}")
        st.info("Start the API in another terminal: `uvicorn backend.main:app --reload`")
        return False

    tab_login, tab_register = st.tabs(["Sign in", "Create account"])
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign in", type="primary")
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
            email = st.text_input("Email", key="r_email")
            name = st.text_input("Name (optional)", key="r_name")
            password = st.text_input("Password (8+ characters)", type="password", key="r_pw")
            submit = st.form_submit_button("Create account", type="primary")
        if submit:
            try:
                api.register(email.strip(), password, full_name=name.strip() or None)
                tok = api.login(email.strip(), password)
                st.session_state["auth_token"] = tok["access_token"]
                st.session_state["auth_email"] = email.strip()
                st.rerun()
            except api.ApiError as e:
                st.error(str(e))
    return False


def _sidebar() -> str:
    st.sidebar.title(":crossed_swords: Kensei")
    st.sidebar.caption("AutoML platform")
    try:
        h = api.health()
        st.sidebar.success(f"API: {h.get('app')} v{h.get('version')}")
    except Exception as e:
        st.sidebar.error(f"API down: {e}")
    email = st.session_state.get("auth_email", "?")
    st.sidebar.markdown(f"**Signed in:** `{email}`")
    if st.sidebar.button("Sign out"):
        _logout()
        st.rerun()
    return st.sidebar.radio(
        "Pages",
        ["Autopilot", "Datasets", "Jobs", "Deployments", "Predict"],
        index=0,
    )


def _render_analysis(analysis: Dict[str, Any]) -> None:
    rows = analysis["rows"]
    ncols = analysis["columns_count"]
    suggested = analysis.get("suggested_target")
    task = analysis.get("suggested_task_type")

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{rows:,}")
    c2.metric("Columns", ncols)
    c3.metric("Suggested target", suggested or "—")
    if task:
        st.info(f"This looks like a **{task}** problem.")
    for w in analysis.get("warnings") or []:
        st.warning(w)

    df = pd.DataFrame(analysis["columns"])
    if not df.empty:
        df = df[["name", "dtype", "unique", "missing", "missing_pct", "id_like", "constant", "sample_values"]].copy()
        df["sample_values"] = df["sample_values"].apply(
            lambda xs: ", ".join(str(x) for x in xs) if isinstance(xs, list) else str(xs)
        )
        df["missing_pct"] = (df["missing_pct"] * 100).round(1).astype(str) + "%"
        st.dataframe(df, use_container_width=True, hide_index=True)


def _page_autopilot(token: str) -> None:
    st.header("Autopilot — upload a CSV, get a model")
    st.caption(
        "Drop your CSV below. We'll analyze it, pick a target, train the best model, "
        "and (optionally) deploy it as an API."
    )

    file = st.file_uploader(
        "CSV file (drag-and-drop or click to browse)",
        type=["csv"],
        help="Maximum 200 MB. Other formats: convert to CSV first.",
    )

    if file is not None and st.session_state.get("active_dataset_filename") != file.name:
        with st.spinner("Uploading..."):
            try:
                ds = api.upload_csv(token, file.name, file.getvalue())
                st.session_state["active_dataset"] = ds
                st.session_state["active_dataset_filename"] = file.name
                st.session_state.pop("active_analysis", None)
                st.success(f"Uploaded: **{ds['name']}** ({ds['rows']:,} rows × {ds['columns']} cols)")
            except api.ApiError as e:
                st.error(str(e))

    ds = st.session_state.get("active_dataset")
    if ds is None:
        existing = api.list_datasets(token)
        if existing:
            st.markdown("**Or pick an earlier upload:**")
            options = {f"#{d['id']} — {d['name']} ({d['rows']:,}×{d['columns']})": d for d in existing}
            label = st.selectbox("Dataset", list(options.keys()), key="reuse_ds")
            if st.button("Use this dataset"):
                st.session_state["active_dataset"] = options[label]
                st.session_state["active_dataset_filename"] = options[label]["filename"]
                st.session_state.pop("active_analysis", None)
                st.rerun()
        return

    if "active_analysis" not in st.session_state:
        with st.spinner("Analyzing your data..."):
            try:
                st.session_state["active_analysis"] = api.analyze_dataset(token, ds["id"])
            except api.ApiError as e:
                st.error(str(e))
                return

    analysis = st.session_state["active_analysis"]

    st.subheader("Your data at a glance")
    _render_analysis(analysis)

    st.subheader("Train a model")
    cols = [c["name"] for c in analysis["columns"]]
    suggested = analysis.get("suggested_target") or (cols[0] if cols else "")
    target_idx = cols.index(suggested) if suggested in cols else 0
    target = st.selectbox(
        "What do you want to predict?",
        cols,
        index=target_idx,
        help="The column the model will learn to predict from the others.",
    )

    preset_label = st.radio(
        "Training speed",
        ["Quick — ~30 sec", "Balanced — ~2 min", "Thorough — ~10 min"],
        index=1,
        horizontal=True,
        help="Quick is good for a first look. Thorough explores more algorithms and hyperparameters.",
    )
    preset = preset_label.split(" ")[0].lower()

    auto_deploy = st.checkbox(
        "Auto-deploy the best model as an API after training",
        value=True,
        help="Generates an endpoint + API key you can call to make predictions.",
    )
    deploy_slug = ""
    if auto_deploy:
        deploy_slug = st.text_input(
            "Endpoint name (optional)",
            placeholder=f"e.g. {ds['name'].lower().replace(' ', '-')}-v1",
        )

    if st.button("Start training", type="primary", use_container_width=True):
        payload: Dict[str, Any] = {
            "dataset_id": ds["id"],
            "target": target,
            "preset": preset,
            "auto_deploy": auto_deploy,
            "deploy_slug": deploy_slug.strip() or None,
        }
        with st.spinner("Training... this may take a while for larger datasets."):
            try:
                result = api.autopilot_train(token, payload)
                st.session_state["last_autopilot"] = result
            except api.ApiError as e:
                st.error(str(e))
                return

    result = st.session_state.get("last_autopilot")
    if result is None:
        return

    job = result["job"]
    if job["status"] == "succeeded":
        st.success(f"Training complete. Best model: **{result['best_model']['algorithm']}**")
        m = result["best_model"]
        cmetrics = m.get("metrics") or {}
        if cmetrics:
            metric_cols = st.columns(min(4, len(cmetrics)))
            for i, (k, v) in enumerate(list(cmetrics.items())[:4]):
                metric_cols[i].metric(k, f"{v:.4f}" if isinstance(v, (int, float)) else str(v))
        if result.get("deployment_slug"):
            st.markdown("### Your live endpoint")
            st.code(result["deployment_endpoint"], language=None)
            st.warning(
                f"API key (shown once — save it now):\n\n`{result['deployment_api_key']}`"
            )
            st.markdown(
                "Use it from anywhere:\n"
                f"```bash\n"
                f"curl -X POST http://localhost:8000{result['deployment_endpoint']} \\\n"
                f"  -H \"X-API-Key: {result['deployment_api_key']}\" \\\n"
                "  -H \"Content-Type: application/json\" \\\n"
                "  -d '{\"rows\":[{...feature values...}]}'\n"
                "```"
            )
    elif job["status"] == "failed":
        st.error(f"Training failed: {job.get('message') or 'unknown error'}")
    else:
        st.info(f"Job #{job['id']} status: {job['status']}")

    with st.expander("Job details"):
        st.json(result)


def _page_datasets(token: str) -> None:
    st.header("Datasets")
    ds_list = api.list_datasets(token)
    if not ds_list:
        st.info("No datasets yet. Use the Autopilot page to upload one.")
        return
    st.dataframe(pd.DataFrame(ds_list), use_container_width=True, hide_index=True)


def _page_jobs(token: str) -> None:
    st.header("Jobs")
    jobs = api.list_jobs(token)
    if not jobs:
        st.info("No jobs yet.")
        return
    df = pd.DataFrame(jobs)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _page_deployments(token: str) -> None:
    st.header("Deployments")
    deps = api.list_deployments(token)
    if not deps:
        st.info("No deployments yet. Train a model with auto-deploy enabled.")
        return
    st.dataframe(pd.DataFrame(deps), use_container_width=True, hide_index=True)


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

    mode = st.radio("Input format", ["JSON rows", "CSV upload"], horizontal=True)
    rows: list = []
    if mode == "JSON rows":
        default = json.dumps([{"feature_1": 0, "feature_2": 0}], indent=2)
        text = st.text_area("Rows", value=default, height=200)
        try:
            rows = json.loads(text)
            if not isinstance(rows, list):
                st.error("Provide a JSON array of objects.")
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
    page = _sidebar()
    if page == "Autopilot":
        _page_autopilot(token)
    elif page == "Datasets":
        _page_datasets(token)
    elif page == "Jobs":
        _page_jobs(token)
    elif page == "Deployments":
        _page_deployments(token)
    elif page == "Predict":
        _page_predict(token)


if __name__ == "__main__":
    main()
else:
    main()
