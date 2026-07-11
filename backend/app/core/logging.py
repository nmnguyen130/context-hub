import logging.config
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Sets up unified logging configuration for development and production environments."""
    log_format = (
        '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
        '"message": "%(message)s", "request_id": "%(request_id)s"}'
        if settings.ENVIRONMENT == "production"
        else "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
    )

    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            from app.core.context import current_context_or_none

            ctx = current_context_or_none()
            record.request_id = ctx.request_id if ctx else "-"
            return True

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            }
        },
        "formatters": {
            "default": {
                "format": log_format,
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "filters": ["request_id"],
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)
