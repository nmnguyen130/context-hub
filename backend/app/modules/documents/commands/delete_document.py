import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceError
from app.core.storage import StorageProvider
from app.modules.documents.models import Document


class DeleteDocumentCommand:
    """Application Service / Use Case executing document deletion.

    Deletes the document database record and all associated assets in S3.

    Attributes:
        db (AsyncSession): Database session.
        storage (StorageProvider): Storage client interface.
    """

    def __init__(self, db: AsyncSession, storage: StorageProvider) -> None:
        self.db = db
        self.storage = storage

    async def execute(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Executes the document deletion flow.

        Args:
            document_id (uuid.UUID): Target document ID to delete.
            tenant_id (uuid.UUID): Tenant owner ID.

        Raises:
            ServiceError: If target document cannot be resolved or accessed.
        """
        # 1. Fetch document record
        stmt = select(Document).where(
            Document.id == document_id, Document.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
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
        await self.db.delete(doc)
        await self.db.commit()
