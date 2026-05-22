import sys
from loguru import logger

from backend.core.config import settings


def _configure() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
        enqueue=False,
    )
    log_file = settings.DATA_DIR / "kensei.log"
    logger.add(
        log_file,
        level="INFO",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
    )


_configure()

__all__ = ["logger"]
