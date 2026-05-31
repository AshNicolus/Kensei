# Kensei — Web Frontend

React + TypeScript app for the Kensei AutoML platform. Replaces the Streamlit
prototype. Designed as the first **module** in a larger ML platform — the
sidebar lists Pretraining and Fine-tuning as "Coming soon" because those are
the next two modules on the roadmap.

## Stack

| | |
|---|---|
| Build | Vite 5 |
| Language | TypeScript 5 (strict) |
| UI | React 18 |
| Styling | Tailwind 3 + shadcn/ui primitives (inlined) |
| Routing | React Router 6 |
| Server state | TanStack Query 5 |
| HTTP | Axios with JWT interceptor + 401 auto-logout |
| Forms | Bare React state (small enough not to need RHF yet) |
| Charts | Recharts |
| Toasts | Sonner |
| Icons | Lucide |

Dark theme by default, generous whitespace, monospace numerics — Linear /
Vercel-style aesthetic.

## Run

```bash
# from frontend-react/
npm install
npm run dev
```

App: http://localhost:5173
Vite proxies `/api/*` and `/health` to `http://localhost:8000` so the FastAPI
backend doesn't need a CORS workaround during dev.

## Structure

```
src/
├─ app/                       # router + top-level App
├─ shared/
│  ├─ components/
│  │  ├─ ui/                  # shadcn primitives (button, card, input, …)
│  │  └─ layout/              # AppShell, Sidebar, Topbar, ComingSoon
│  ├─ hooks/                  # use-auth
│  └─ lib/                    # axios client + utils
├─ pages/auth/                # Login, Register, AuthLayout
└─ modules/
   └─ automl/                 # the only module wired up today
      ├─ api/                 # typed clients + types.ts
      ├─ components/          # Dropzone, StatusBadge, FeatureImportanceChart
      └─ pages/               # Autopilot, Datasets, Jobs, JobDetail, Deployments, Predict
```

Each future module (Pretraining, Fine-tuning, …) gets its own `modules/<name>/`
folder with the same shape. The sidebar reads from a small `MODULES` array in
`Sidebar.tsx` — adding a new module is one entry there + one folder.

## What's wired up

- Email / password auth → calls `/api/auth/register`, `/api/auth/login`,
  `/api/auth/me`. JWT cached in `localStorage`, attached to every request.
- 401 anywhere triggers a logout + redirect to `/login`.
- **Autopilot** flow: drop a CSV → auto-analyze → suggested target + task type
  → speed preset (Quick / Balanced / Thorough) → auto-deploy toggle → one click
  trains the best model and shows feature-importance chart + live endpoint +
  one-time API key.
- Datasets, Jobs (with auto-poll while running), Job detail (candidate models
  + feature importance chart), Deployments, Predict (test a deployed model).

## Production build

```bash
npm run build
```

Outputs static assets to `dist/`. Serve with any CDN; the API URL can be set
via `VITE_API_URL` at build time.

## Not yet (Phase 2.1+)

- Public landing page (`/` for unauthed = redirect to /login today)
- Account / billing pages
- Mobile sidebar drawer
- Pretraining + Fine-tuning module bodies
