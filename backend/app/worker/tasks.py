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


@celery_app.task(bind=True, max_retries=3)
def parse_document_task(self, document_id: str) -> None:
    """Celery task running synchronous event loop to invoke async parsing logic."""
    import botocore.exceptions
    import sqlalchemy.exc

    from app.modules.documents.commands.ingest_document import (
        mark_document_as_error,
        run_ingestion,
    )

    try:
        asyncio.run(run_ingestion(document_id))
    except (
        botocore.exceptions.BotoCoreError,
        sqlalchemy.exc.OperationalError,
        OSError,
    ) as infra_err:
        retry_count = self.request.retries
        countdown = 2**retry_count
        try:
            raise self.retry(exc=infra_err, countdown=countdown)
        except self.MaxRetriesExceededError:
            # All retries exhausted: mark document as ERROR
            asyncio.run(
                mark_document_as_error(
                    document_id,
                    f"Infrastructure failure (retries exhausted): {str(infra_err)}",
                )
            )
            raise infra_err
    except Exception as logic_err:
        # Non-infrastructure logical error: already handled inside usecase
        raise logic_err


@celery_app.task
def debug_task() -> None:
    print("Celery works successfully!")
