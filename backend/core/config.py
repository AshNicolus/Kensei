from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "Kensei"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = True

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    DATABASE_URL: str = "sqlite:///./kensei.db"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_EAGER: bool = False

    MLFLOW_TRACKING_URI: str = "file:./data/mlruns"
    MLFLOW_EXPERIMENT: str = "kensei"

    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    DATA_DIR: Path = PROJECT_ROOT / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    MODELS_DIR: Path = DATA_DIR / "models"
    ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"

    MAX_UPLOAD_MB: int = 200
    ALLOWED_UPLOAD_EXT: List[str] = Field(default_factory=lambda: [".csv"])

    OPTUNA_TRIALS: int = 15
    CV_FOLDS: int = 3
    RANDOM_STATE: int = 42

    SECRET_KEY: str = "change-me-in-prod"
    API_KEY_HEADER: str = "X-API-Key"

    # If non-empty, overrides the dev CORS origin list. Comma-separated env var.
    CORS_ORIGINS: List[str] = Field(default_factory=list)

    def ensure_dirs(self) -> None:
        for p in (self.DATA_DIR, self.UPLOADS_DIR, self.MODELS_DIR, self.ARTIFACTS_DIR):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
