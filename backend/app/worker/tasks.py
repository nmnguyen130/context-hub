import asyncio
import logging
import uuid

from celery import Celery, Task

from app.core.config import settings
from app.core.context import RequestContext, bind_context, try_current_context
from app.core.database import owner_session
from app.core.uow import UnitOfWork
from app.infrastructure.storage import S3StorageProvider
from app.modules.documents.services.ingestion_service import IngestionService

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
    imports=("app.worker.tasks",),
)


class ContextTask(Task):
    """Celery task with automatic RequestContext restoration."""

    def __call__(self, *args, **kwargs):
        ctx_data = kwargs.get("context")
        if ctx_data:
            ctx = RequestContext.from_dict(ctx_data)
            with bind_context(ctx):
                return self.run(*args, **kwargs)
        return self.run(*args, **kwargs)


celery_app.Task = ContextTask


@celery_app.task(name="documents.process_ingestion", bind=True, base=ContextTask)
def process_ingestion_task(self, payload: dict, context: dict | None = None) -> None:
    """Celery task for async document ingestion."""
    document_id_str = payload.get("document_id")
    if not document_id_str:
        logger.error("Missing document_id in ingestion payload")
        return

    ctx = try_current_context() or RequestContext(
        request_id=(context or {}).get("request_id", ""),
        trace_id=(context or {}).get("trace_id", ""),
        tenant_id=uuid.UUID(payload["tenant_id"])
        if payload and payload.get("tenant_id")
        else None,
    )

    async def _ingest():
        async with UnitOfWork(owner_session, ctx, is_admin=True) as uow:
            await IngestionService(uow, S3StorageProvider()).process_document(
                uuid.UUID(document_id_str)
            )

    asyncio.run(_ingest())
