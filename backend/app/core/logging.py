# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import logging.config
import os

from pythonjsonlogger import jsonlogger

from .config import get_settings
from .audit_log import init_audit_logger

# Create logs directory first (before any logging setup)
# Use /tmp/logs in containers if /app/logs is not writable
try:
    os.makedirs("logs", exist_ok=True)
    LOG_DIR = "logs"
except PermissionError:
    os.makedirs("/tmp/logs", exist_ok=True)
    LOG_DIR = "/tmp/logs"


def setup_logging() -> None:
    settings = get_settings()

    # Base logging config
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(timestamp)s %(levelname)s %(name)s %(message)s %(exc_info)s",
                "timestamp": True,
            },
            "text": {
                "format": "[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "[%(asctime)s] %(name)s (%(filename)s:%(lineno)d) - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": settings.log_format,
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": settings.log_format,
                "filename": f"{LOG_DIR}/app.log",
                "maxBytes": 104857600,  # 100MB
                "backupCount": 10,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": settings.log_format,
                "filename": f"{LOG_DIR}/error.log",
                "maxBytes": 104857600,  # 100MB
                "backupCount": 10,
            },
        },
        "loggers": {
            "app": {
                "level": settings.log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": settings.log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": settings.log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console", "file"],
        },
    }

    # Apply configuration
    logging.config.dictConfig(logging_config)

    # Initialize audit logger AFTER dictConfig so log messages use configured handlers
    if settings.audit_log_enabled:
        try:
            signing_key = settings.audit_log_signing_key or settings.secret_key
            init_audit_logger(signing_key, settings.audit_log_path)
            logging.getLogger(__name__).info(
                "Audit logging initialized", extra={"audit_log_path": settings.audit_log_path}
            )
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Failed to initialize audit logging: {e}", exc_info=True
            )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
