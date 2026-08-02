import hashlib
import io
import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.context import RequestContext
from app.core.exceptions import ServiceError
from app.core.pagination import CursorParams, paginate_cursor
from app.core.uow import UnitOfWork
from app.infrastructure.storage import StorageProvider
from app.modules.documents.models import Document, DocumentStatus, Workspace
from app.modules.documents.parsers import detect_mime_type
from app.modules.documents.schemas import WorkspaceCreate, WorkspaceUpdate
from app.modules.tenant.services.tenant_service import generate_slug


class WorkspaceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create(self, tenant_id: uuid.UUID, data: WorkspaceCreate) -> Workspace:
        """Create a new workspace for the tenant, generating a slug if not provided."""
        slug = data.slug or generate_slug(data.name, fallback="workspace")

        existing = await self.uow.session.scalar(
            select(Workspace).where(
                Workspace.tenant_id == tenant_id,
                Workspace.slug == slug,
            )
        )
        if existing:
            raise ServiceError.conflict("Workspace slug already exists.")

        workspace = Workspace(
            tenant_id=tenant_id,
            name=data.name.strip(),
            slug=slug,
            description=data.description,
        )
        self.uow.session.add(workspace)
        await self.uow.flush()
        return workspace

    async def get(self, workspace_id: uuid.UUID) -> Workspace:
        """Retrieve a single workspace by ID."""
        workspace = await self.uow.session.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.is_active.is_(True),
            )
        )
        if workspace is None:
            raise ServiceError.not_found("Workspace")
        return workspace

    async def list(
        self, tenant_id: uuid.UUID, params: CursorParams | None = None
    ) -> tuple[list[Workspace], str | None, bool]:
        """List workspaces for the specified tenant with pagination."""
        params = params or CursorParams()

        stmt = select(Workspace).where(
            Workspace.tenant_id == tenant_id,
            Workspace.is_active.is_(True),
        )
        return await paginate_cursor(
            self.uow.session,
            stmt,
            params,
            sort_column=Workspace.created_at,
            id_column=Workspace.id,
        )

    async def update(self, workspace_id: uuid.UUID, data: WorkspaceUpdate) -> Workspace:
        """Update workspace fields."""
        workspace = await self.get(workspace_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(workspace, key, value)
        await self.uow.flush()
        return workspace


class DocumentService:
    ALLOWED_EXTENSIONS = set(settings.RAG_ALLOWED_EXTENSIONS.split(","))

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def upload(
        self,
        *,
        workspace_id: uuid.UUID,
        filename: str,
        content: bytes,
        content_type: str | None,
        storage: StorageProvider,
        context: RequestContext,
    ) -> Document:
        """Validate and upload a document to object storage, then register it in the database."""
        await self._validate_file(filename, content)

        content_hash = hashlib.sha256(content).hexdigest()
        stmt = select(
            Workspace,
            select(Document.id)
            .where(
                Document.tenant_id == context.tenant_id,
                Document.workspace_id == workspace_id,
                Document.content_hash == content_hash,
            )
            .exists()
            .label("duplicate_exists"),
        ).where(
            Workspace.id == workspace_id,
            Workspace.tenant_id == context.tenant_id,
            Workspace.is_active.is_(True),
        )
        res = (await self.uow.session.execute(stmt)).first()
        if res is None:
            raise ServiceError.not_found("Workspace")

        workspace, duplicate_exists = res._tuple()
        if duplicate_exists:
            raise ServiceError.conflict(
                "Document with identical content already exists."
            )

        mime_type = detect_mime_type(filename, content_type)
        document_id = uuid.uuid4()
        storage_key = (
            f"tenants/{context.tenant_id}/documents/{document_id}/v1/{filename}"
        )

        await storage.upload_file(io.BytesIO(content), storage_key)

        document = Document(
            id=document_id,
            tenant_id=context.tenant_id,
            workspace_id=workspace_id,
            filename=filename,
            mime_type=mime_type,
            file_size=len(content),
            content_hash=content_hash,
            storage_key=storage_key,
            version=1,
            uploaded_by=context.user_id,
            status=DocumentStatus.PENDING,
            metadata_={"workspace_name": workspace.name},
        )
        document.record_event(
            "documents.process_ingestion",
            {
                "document_id": str(document_id),
                "tenant_id": str(context.tenant_id),
            },
        )
        self.uow.session.add(document)
        await self.uow.flush()
        return document

    async def get(self, document_id: uuid.UUID) -> Document:
        """Retrieve a single document by ID."""
        document = await self.uow.session.get(Document, document_id)
        if document is None:
            raise ServiceError.not_found("Document")
        return document

    async def reingest(
        self,
        *,
        document_id: uuid.UUID,
        filename: str,
        content: bytes,
        content_type: str | None,
        storage: StorageProvider,
        context: RequestContext,
    ) -> Document:
        """Re-ingest a document with updated content, incrementing its version."""
        await self._validate_file(filename, content)

        document = await self.get(document_id)

        content_hash = hashlib.sha256(content).hexdigest()
        mime_type = detect_mime_type(filename, content_type)
        new_version = document.version + 1
        storage_key = f"tenants/{context.tenant_id}/documents/{document_id}/v{new_version}/{filename}"

        await storage.upload_file(io.BytesIO(content), storage_key)

        document.filename = filename
        document.mime_type = mime_type
        document.file_size = len(content)
        document.content_hash = content_hash
        document.storage_key = storage_key
        document.version = new_version
        document.status = DocumentStatus.PENDING
        document.error_message = None

        document.record_event(
            "documents.process_ingestion",
            {
                "document_id": str(document.id),
                "tenant_id": str(context.tenant_id),
            },
        )
        await self.uow.flush()
        return document

    async def list_by_workspace(
        self,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        params: CursorParams | None = None,
    ) -> tuple[list[Document], str | None, bool]:
        """List documents belonging to a workspace with pagination."""
        params = params or CursorParams()

        stmt = select(Document).where(
            Document.tenant_id == tenant_id,
            Document.workspace_id == workspace_id,
        )
        return await paginate_cursor(
            self.uow.session,
            stmt,
            params,
            sort_column=Document.created_at,
            id_column=Document.id,
        )

    async def delete(self, document_id: uuid.UUID, storage: StorageProvider) -> None:
        """Delete a document from object storage and the database."""
        document = await self.get(document_id)
        keys_to_delete = [document.storage_key]
        if document.status == DocumentStatus.ACTIVE:
            keys_to_delete.append(document.extracted_text_key)

        for key in keys_to_delete:
            await storage.delete_file(key)

        await self.uow.session.delete(document)
        await self.uow.flush()

    async def _validate_file(self, filename: str, content: bytes) -> None:
        """Validate file size and extension restrictions."""
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise ServiceError(
                f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB.",
                status_code=413,
            )

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ServiceError(
                f"Unsupported file type. Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}",
                status_code=415,
            )
