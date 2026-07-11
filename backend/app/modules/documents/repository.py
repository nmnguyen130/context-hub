# app/modules/documents/repository.py
import uuid
from app.core.repository import Repository
from app.modules.documents.models import Document, DocumentChunk, Workspace

class WorkspaceRepository(Repository[Workspace]):
    model = Workspace

class DocumentRepository(Repository[Document]):
    model = Document

    async def get_by_workspace(self, workspace_id: uuid.UUID) -> list[Document]:
        stmt = self.query().where(Document.workspace_id == workspace_id)
        result = await self.session.scalars(stmt)
        return list(result)

class DocumentChunkRepository(Repository[DocumentChunk]):
    model = DocumentChunk
