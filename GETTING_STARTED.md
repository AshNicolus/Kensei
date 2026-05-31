# Getting Started with Kensei

This guide walks you through running Kensei on your machine from scratch. No prior backend / Docker / ML experience required.

> **What you'll have at the end:** a local web app at `http://localhost:8501` where you can drag a CSV in, click one button, and get a trained model deployed as an API endpoint.

---

## 0. What you need

- **Windows, macOS, or Linux** — any modern OS.
- **Python 3.10, 3.11, or 3.12** installed.
  Check by opening a terminal and running:
  ```powershell
  python --version
  ```
  If you don't have it, grab the latest from [python.org/downloads](https://www.python.org/downloads/). Tick **"Add Python to PATH"** during install.
- **Git** (to clone the repo). [git-scm.com/downloads](https://git-scm.com/downloads).
- (Optional) **Docker Desktop** — only if you want the full production-style stack with Postgres + Redis. Skip for now.

That's it. **No Docker required to try Kensei.**

---

## 1. Clone the repo

In PowerShell (Windows) or your terminal:

```powershell
cd $HOME\Desktop
git clone https://github.com/AshNicolus/Kensei.git
cd Kensei
```

---

## 2. Create a virtual environment

A virtual environment keeps Kensei's packages separate from anything else on your machine.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you see an "execution policy" error, run this **once** in PowerShell, then activate again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should now see `(.venv)` at the start of your prompt.

---

## 3. Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

This downloads everything Kensei needs (FastAPI, scikit-learn, Streamlit, etc.). Takes a few minutes the first time.

---

## 4. Run the app — two terminals

Kensei has two pieces: a **backend API** that does the ML work, and a **frontend UI** built with Streamlit. Run each in its own terminal.

> In every terminal, make sure `(.venv)` is active. If not, run the activation command from step 2 again.

### Terminal 1 — Start the backend

```powershell
uvicorn backend.main:app --reload
```

You should see:
```
Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000
```

Leave this terminal running. Open `http://localhost:8000/health` in your browser — you should see `{"status":"ok",...}`.

### Terminal 2 — Start the UI

Open a **second** PowerShell window, activate `.venv` again, then:

```powershell
streamlit run frontend/streamlit_app/main.py
```

Your browser will pop open automatically at `http://localhost:8501`.

---

## 5. Use it

1. **Create an account** — first time only. Email + 8-character password.
2. **Autopilot page** — drag your CSV into the upload box (or click to browse). Kensei analyses your data automatically and suggests a target column.
3. Pick the column you want to predict (the suggestion is usually right).
4. Pick a speed: **Quick** (30s), **Balanced** (2min), or **Thorough** (10min).
5. Leave "Auto-deploy" checked.
6. Click **Start training**.
7. When it finishes, you'll see the best model's metrics and a live API endpoint with a key. Copy the key — it's only shown once.

That's the full loop: **CSV → trained model → live prediction API**, in a couple of clicks.

---

## 6. Calling your deployed model

After auto-deploy, you'll see something like:

```
/api/deployments/my-model/predict
API key: ks_abc123...
```

You can call it from any tool:

```bash
curl -X POST http://localhost:8000/api/deployments/my-model/predict \
  -H "X-API-Key: ks_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"rows":[{"feature_1": 0.5, "feature_2": "value"}]}'
```

The keys in `rows` are the column names from your CSV (minus the target).

---

## 7. Common problems

### "ModuleNotFoundError: No module named 'backend'" or "'frontend'"
You forgot to activate `.venv`, or you're running from the wrong folder. Make sure you're in the **`Kensei` repo root** and `(.venv)` shows in your prompt.

### "Connection refused on port 6379"
That's Redis. In dev mode Kensei is supposed to run training inline (no Redis needed). If you see this error, check your `backend/workers/celery_app.py` is up to date — the latest version auto-skips Redis when `ENV` is `development`, `dev`, or `test`. Just `git pull`.

### "execution policy" error on Windows
PowerShell blocks script execution by default. Run this once:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Drag-and-drop isn't working in Streamlit
Use the **"Browse files"** button next to the drop zone. Some browsers (or browser extensions) block drag-and-drop from the OS.

### Training fails with "no usable rows"
You picked a target column with mostly missing values, or a column that only has one unique value. Try a different column from the dropdown — Kensei's suggested target is usually safe.

### Port 8000 or 8501 already in use
Another process is using the port. Either stop that process or change Kensei's port:
- API: `uvicorn backend.main:app --reload --port 8010`
- UI: `streamlit run frontend/streamlit_app/main.py --server.port 8520`

---

## 8. Stopping the app

In each terminal, press `Ctrl-C`. Done.

To reactivate later: `cd` into the repo, run `.\.venv\Scripts\Activate.ps1`, then the two `uvicorn` and `streamlit run` commands again.

---

## 9. What's next

- **Running the test suite:** `pip install pytest && python -m pytest tests/` — should be 33 passing.
- **Switching to production mode:** set `ENV=production` in a `.env` file at the repo root. Then you need Redis (`docker run -d -p 6379:6379 redis:7-alpine`) and to start a Celery worker (`celery -A backend.workers.celery_app worker --pool=solo`).
- **Postgres instead of SQLite:** set `DATABASE_URL=postgresql://user:pass@host:5432/dbname` in `.env`.
- **Multi-user:** already supported — anyone you give the URL can register their own account. Their data is invisible to others.

---

Stuck? Open an issue at [github.com/AshNicolus/Kensei/issues](https://github.com/AshNicolus/Kensei/issues).
