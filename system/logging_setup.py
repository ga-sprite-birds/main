"""Logging setup for Core and API entry points."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from system.config import settings


def configure_logging(name: str, *, log_file: Path | None = None) -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return
    formatter = logging.Formatter(settings.LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    if settings.LOG_CONSOLE:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
    target = Path(log_file or settings.LOG_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        target,
        maxBytes=settings.LOG_MAX_FILE_SIZE * 1024 * 1024,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    logging.getLogger(name).info("Logging initialized")
