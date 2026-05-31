from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.deps import init_db
from backend.api.routers import auth, autopilot, deploy, jobs, predict, upload
from backend.api.routers.predict import warmup_deployments
from backend.core.config import settings
from backend.core.logger import logger
from backend.registry.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"starting {settings.APP_NAME} {settings.APP_VERSION} env={settings.ENV}")
    init_db()
    try:
        warmup_deployments()
    except Exception as e:
        logger.warning(f"warmup skipped: {e}")
    yield
    logger.info("shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AutoML platform — CSV to deployed API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(app=settings.APP_NAME, version=settings.APP_VERSION)


app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(deploy.router, prefix="/api")
app.include_router(autopilot.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
