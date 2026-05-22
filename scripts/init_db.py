"""Initialize the Kensei database (create all tables).

Usage:
    python -m scripts.init_db
"""
from __future__ import annotations

from backend.api.deps import init_db
from backend.core.config import settings
from backend.core.logger import logger


def main() -> None:
    logger.info(f"init_db: using DATABASE_URL={settings.DATABASE_URL}")
    settings.ensure_dirs()
    init_db()
    logger.info("init_db: done")


if __name__ == "__main__":
    main()
