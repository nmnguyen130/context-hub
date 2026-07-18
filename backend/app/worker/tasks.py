import logging

from celery import Celery, Task

from app.core.config import settings
from app.core.context import RequestContext, bind_context

logger = logging.getLogger(__name__)

celery_app = Celery(
    "app_worker",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
)


class ContextTask(Task):
    """Celery task with automatic RequestContext restoration."""

    def __call__(self, *args, **kwargs):
        ctx_data = kwargs.pop("context", None)
        if ctx_data:
            ctx = RequestContext.from_dict(ctx_data)
            with bind_context(ctx):
                return self.run(*args, **kwargs)
        return self.run(*args, **kwargs)


celery_app.Task = ContextTask
