# app/modules/documents/commands/delete_document.py
import uuid
from app.core.exceptions import ServiceError
from app.core.storage import StorageProvider
from app.core.uow import UnitOfWork
from app.modules.documents.repository import DocumentRepository
from app.core.events import DomainEvent

class DeleteDocumentCommand:
    """Application Service / Use Case executing document deletion."""

    def __init__(self, uow: UnitOfWork, storage: StorageProvider) -> None:
        self.uow = uow
        self.storage = storage

    async def execute(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Executes the document deletion flow."""
        doc_repo = self.uow.repo(DocumentRepository)
        doc = await doc_repo.get(document_id)
        if not doc or doc.tenant_id != tenant_id:
            raise ServiceError(
                f"Document not found or access denied: {document_id}",
                status_code=404,
            )

        # 2. Delete S3 raw file
        try:
            await self.storage.delete_file(doc.object_store_key)
        except Exception:
            pass  # Ignore S3 missing files to prevent blocking deletion

        # 3. Delete S3 extracted text file
        try:
            raw_key_prefix = doc.object_store_key.rsplit("/", 1)[0]
            extracted_key = f"{raw_key_prefix}/extracted.txt"
            await self.storage.delete_file(extracted_key)
        except Exception:
            pass

        # 4. Delete database record
        await doc_repo.delete(doc)
        
        # Record document deleted domain event
        self.uow.record_event(DomainEvent(
            event_type="document.deleted",
            payload={
                "document_id": str(doc.id),
                "tenant_id": str(tenant_id),
                "workspace_id": str(doc.workspace_id) if doc.workspace_id else None,
                "name": doc.name
            }
        ))
        await self.uow.flush()
