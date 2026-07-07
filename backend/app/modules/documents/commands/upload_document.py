import hashlib
import io
import uuid
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceError
from app.core.storage import StorageProvider
from app.modules.documents.models import Document, Workspace


class UploadDocumentCommand:
    """Application Service / Use Case executing document uploads.

    Coordinates database records insertion, raw file uploads to the object
    storage provider, and celery task dispatch.

    Attributes:
        db (AsyncSession): Database session.
        storage (StorageProvider): Storage client interface.
    """

    def __init__(self, db: AsyncSession, storage: StorageProvider) -> None:
        self.db = db
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
        """Executes the document upload flow.

        Args:
            tenant_id (uuid.UUID): Tenant owner ID.
            workspace_id (uuid.UUID): Target workspace ID.
            filename (str): Source filename.
            file_size (int): Size of the file in bytes.
            file_obj (BinaryIO): Binary stream of the file content.
            mime_type (str | None): File MIME type.

        Returns:
            Document: The newly created Document database model instance.

        Raises:
            ServiceError: If target workspace cannot be resolved or accessed.
        """
        # 1. Verify workspace ownership
        workspace = await self._get_workspace(workspace_id, tenant_id)
        if not workspace:
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
        self.db.add(doc)

        # 3. Upload to S3 + checksum
        content = file_obj.read()
        doc.checksum = hashlib.sha256(content).hexdigest()
        await self.storage.upload_file(io.BytesIO(content), object_key)

        # 4. Commit
        await self.db.commit()
        await self.db.refresh(doc)

        # 5. Dispatch background worker
        from app.worker.tasks import parse_document_task

        parse_document_task.delay(str(doc.id))

        return doc

    async def _get_workspace(
        self, ws_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Workspace | None:
        stmt = select(Workspace).where(
            Workspace.id == ws_id, Workspace.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _extract_extension(filename: str) -> str:
        parts = filename.rsplit(".", 1)
        return parts[-1].lower() if len(parts) > 1 else "bin"
