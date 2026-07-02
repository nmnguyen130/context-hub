import asyncio
import io
import uuid

import boto3
import botocore.exceptions
import sqlalchemy.exc
from celery import Celery

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.storage import get_storage_client
from app.modules.documents.models import Document
from app.modules.documents.parsers import parser_registry

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


async def _async_parse_document(self_task, document_id: str) -> None:
    """Async handler for document download, text extraction, and storage."""
    # 1. Open DB session with tenant filter disabled for background worker
    async with AsyncSessionLocal() as db:
        stmt = (
            sqlalchemy.select(Document)
            .where(Document.id == uuid.UUID(document_id))
            .execution_options(skip_tenant_filter=True)
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found in database.")

        # 2. Update status to PARSING
        doc.status = "PARSING"
        doc.error_message = None
        await db.commit()
        await db.refresh(doc)

        try:
            # 3. Download raw bytes from S3
            storage = get_storage_client()
            content = storage.download_file(doc.object_store_key)

            # 4. Resolve parser and parse file contents
            parser = parser_registry.get_parser(doc.name)
            extracted_text = parser.parse(content)

            # 5. Upload parsed plain text to S3 (same parent directory)
            raw_key_prefix = doc.object_store_key.rsplit("/", 1)[0]
            extracted_key = f"{raw_key_prefix}/extracted.txt"
            extracted_stream = io.BytesIO(extracted_text.encode("utf-8"))
            storage.upload_file(extracted_stream, extracted_key)

            # 6. Update status to ACTIVE
            doc.status = "ACTIVE"
            await db.commit()

        except (
            boto3.exceptions.Boto3Error,
            botocore.exceptions.BotoCoreError,
            sqlalchemy.exc.OperationalError,
            OSError,
        ) as infra_err:
            await db.rollback()
            # Infrastructure exception: request Celery retry with exponential backoff
            retry_count = self_task.request.retries
            countdown = 2**retry_count
            try:
                raise self_task.retry(exc=infra_err, countdown=countdown, max_retries=3)
            except self_task.MaxRetriesExceededError:
                # All retries exhausted: mark document as ERROR
                doc.status = "ERROR"
                doc.error_message = (
                    f"Infrastructure failure (retries exhausted): {str(infra_err)}"[
                        :255
                    ]
                )
                await db.commit()
                raise infra_err

        except Exception as logic_err:
            await db.rollback()
            # Logical exception (unsupported format, corrupt file): mark as ERROR immediately
            doc.status = "ERROR"
            doc.error_message = f"Parsing failed: {str(logic_err)}"[:255]
            await db.commit()
            raise logic_err


@celery_app.task(bind=True)
def parse_document_task(self, document_id: str) -> None:
    """Celery task running synchronous event loop to invoke async parsing logic."""
    asyncio.run(_async_parse_document(self, document_id))


@celery_app.task
def debug_task() -> None:
    print("Celery works successfully!")
