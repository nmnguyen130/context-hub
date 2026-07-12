import logging
import logging.config
import sys

from app.core.context import try_current_context


class ContextFilter(logging.Filter):
    """Injects RequestContext fields into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = try_current_context()
        record.request_id = ctx.request_id if ctx else "-"
        record.trace_id = ctx.trace_id if ctx else "-"
        record.tenant_id = str(ctx.tenant_id) if ctx and ctx.tenant_id else "-"
        return True


def setup_logging() -> None:
    """Sets up global logging configuration."""
    log_format = (
        "%(asctime)s | %(levelname)s | %(name)s | "
        "request=%(request_id)s trace=%(trace_id)s "
        "tenant=%(tenant_id)s | %(message)s"
    )

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context": {
                "()": ContextFilter,
            }
        },
        "formatters": {
            "default": {
                "format": log_format,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "filters": ["context"],
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(logging_config)
