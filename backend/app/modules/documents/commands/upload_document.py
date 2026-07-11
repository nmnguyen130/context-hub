# app/modules/documents/commands/upload_document.py
import hashlib
import io
import uuid
from typing import BinaryIO
from sqlalchemy import select
from app.core.exceptions import ServiceError
from app.core.storage import StorageProvider
from app.core.uow import UnitOfWork
from app.core.context import current_context
from app.core.events import DomainEvent
from app.modules.documents.models import Document, Workspace
from app.modules.documents.repository import DocumentRepository, WorkspaceRepository

class UploadDocumentCommand:
    """Application Service / Use Case executing document uploads.

    Coordinates database records insertion, raw file uploads to the object
    storage provider, and celery task dispatch.
    """

    def __init__(self, uow: UnitOfWork, storage: StorageProvider) -> None:
        self.uow = uow
        self.storage = storage

    async def execute(
        self,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        filename: str,
        file_size: int,
        file_obj: BinaryIO,
        mime_type: str | None = None,
    ) -> Document:
        """Executes the document upload flow."""
        ws_repo = self.uow.repo(WorkspaceRepository)
        doc_repo = self.uow.repo(DocumentRepository)

        # 1. Verify workspace ownership
        workspace = await ws_repo.get(workspace_id)
        if not workspace or workspace.tenant_id != tenant_id:
            raise ServiceError(
                f"Workspace not found or access denied: {workspace_id}",
                status_code=404,
            )

        # 2. Build document record
        ext = self._extract_extension(filename)
        doc_id = uuid.uuid4()
        object_key = f"{tenant_id}/{workspace_id}/{doc_id}/raw.{ext}"

        doc = Document(
            id=doc_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            name=filename,
            file_type=ext,
            object_store_key=object_key,
            status="PENDING",
            file_size=file_size,
            mime_type=mime_type,
        )
        await doc_repo.add(doc)

        # 3. Upload to S3 + checksum
        content = file_obj.read()
        doc.checksum = hashlib.sha256(content).hexdigest()
        await self.storage.upload_file(io.BytesIO(content), object_key)

        # 4. Flush to DB so the record is visible when task runs
        await self.uow.flush()

        # 5. Dispatch background worker with context dict propagation
        from app.worker.tasks import parse_document_task
        ctx_dict = current_context().to_dict()

        # UoW records the event
        self.uow.record_event(DomainEvent(
            event_type="document.uploaded",
            payload={
                "document_id": str(doc.id),
                "tenant_id": str(tenant_id),
                "workspace_id": str(workspace_id),
                "name": filename
            }
        ))

        # We trigger task.delay
        parse_document_task.delay(str(doc.id), ctx_dict)

        return doc

    @staticmethod
    def _extract_extension(filename: str) -> str:
        parts = filename.rsplit(".", 1)
        return parts[-1].lower() if len(parts) > 1 else "bin"
