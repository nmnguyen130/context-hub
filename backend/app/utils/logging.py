import json
import logging
import logging.config
import sys
from datetime import UTC, datetime

from app.core.context import try_current_context


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter injecting RequestContext fields."""

    def format(self, record: logging.LogRecord) -> str:
        ctx = try_current_context()
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": ctx.request_id if ctx else None,
            "trace_id": ctx.trace_id if ctx else None,
            "tenant_id": str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging() -> None:
    """Sets up global logging configuration using JSON format."""
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(logging_config)
