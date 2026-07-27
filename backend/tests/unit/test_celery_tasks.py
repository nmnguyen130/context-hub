import uuid
from unittest.mock import AsyncMock, patch

from app.worker.tasks import celery_app, process_ingestion_task


def test_celery_task_registration():
    """Verify documents.process_ingestion task is registered in Celery app."""
    assert "documents.process_ingestion" in celery_app.tasks


@patch("app.worker.tasks.IngestionService")
@patch("app.worker.tasks.UnitOfWork")
@patch("app.worker.tasks.S3StorageProvider")
def test_process_ingestion_task_execution(
    mock_storage, mock_uow, mock_ingestion_service
):
    """Verify process_ingestion task instantiates IngestionService and processes document."""
    mock_service_instance = AsyncMock()
    mock_ingestion_service.return_value = mock_service_instance

    doc_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    payload = {"document_id": doc_id, "tenant_id": tenant_id}
    context = {"request_id": "req-123", "trace_id": "tr-456"}

    process_ingestion_task(payload=payload, context=context)

    mock_service_instance.process_document.assert_called_once_with(uuid.UUID(doc_id))
