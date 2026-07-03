import asyncio

from celery import Celery

from app.core.config import settings

# Initialize Celery app instance
celery_app = Celery(
    "contexthub_tasks",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "app.worker.tasks.parse_document_task": {"queue": "ingestion"},
    },
)


@celery_app.task(bind=True)
def parse_document_task(self, document_id: str) -> None:
    """Celery task running synchronous event loop to invoke async parsing logic."""
    from app.modules.documents.services import process_document_ingestion

    asyncio.run(process_document_ingestion(self, document_id))


@celery_app.task
def debug_task() -> None:
    print("Celery works successfully!")
