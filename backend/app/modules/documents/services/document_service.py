import hashlib
import io
import re
import uuid

from sqlalchemy import func, select

from app.core.config import settings
from app.core.context import RequestContext, try_current_context
from app.core.exceptions import ServiceError
from app.core.pagination import PaginationParams
from app.core.uow import UnitOfWork
from app.infrastructure.storage import StorageProvider
from app.modules.documents.models import Document, DocumentStatus, Workspace
from app.modules.documents.parsers import EXTENSION_MIME, detect_mime_type
from app.modules.documents.schemas import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create(self, data: WorkspaceCreate) -> Workspace:
        """Create a new workspace for the tenant, generating a slug if not provided."""
        slug = data.slug or self._generate_slug(data.name)
        ctx = try_current_context()
        if not ctx or not ctx.tenant_id:
            raise ServiceError("Tenant context required", status_code=400)

        existing = await self.uow.session.scalar(
            select(Workspace).where(
                Workspace.tenant_id == ctx.tenant_id,
                Workspace.slug == slug,
            )
        )
        if existing:
            raise ServiceError("Workspace slug already exists.", status_code=409)

        workspace = Workspace(
            tenant_id=ctx.tenant_id,
            name=data.name.strip(),
            slug=slug,
            description=data.description,
        )
        self.uow.session.add(workspace)
        await self.uow.flush()
        return workspace

    async def get(self, workspace_id: uuid.UUID) -> Workspace:
        """Retrieve a single workspace by ID."""
        workspace = await self.uow.session.get(Workspace, workspace_id)
        if workspace is None:
            raise ServiceError("Workspace not found.", status_code=404)
        return workspace

    async def list(
        self, pagination: PaginationParams | None = None
    ) -> tuple[list[Workspace], int]:
        """List workspaces for the current tenant with pagination."""
        pagination = pagination or PaginationParams()
        ctx = try_current_context()
        if not ctx or not ctx.tenant_id:
            raise ServiceError("Tenant context required", status_code=400)

        stmt = (
            select(Workspace)
            .where(
                Workspace.tenant_id == ctx.tenant_id,
                Workspace.is_active.is_(True),
            )
            .order_by(Workspace.created_at.desc())
        )
        total = (
            await self.uow.session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            or 0
        )
        items = (
            await self.uow.session.scalars(
                stmt.offset(pagination.offset).limit(pagination.limit)
            )
        ).all()
        return list(items), total

    async def update(self, workspace_id: uuid.UUID, data: WorkspaceUpdate) -> Workspace:
        """Update workspace fields."""
        workspace = await self.get(workspace_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(workspace, key, value)
        await self.uow.flush()
        return workspace

    @staticmethod
    def _generate_slug(name: str) -> str:
        """Generate a URL-safe slug from a workspace name."""
        slug = re.sub(
            r"[\s_-]+",
            "-",
            re.sub(r"[^\w\s-]", "", name.strip().lower()),
        ).strip("-")
        return slug or "workspace"


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

        workspace = await self.uow.session.get(Workspace, workspace_id)
        if workspace is None:
            raise ServiceError("Workspace not found.", status_code=404)

        content_hash = hashlib.sha256(content).hexdigest()
        duplicate = await self.uow.session.scalar(
            select(Document).where(
                Document.tenant_id == context.tenant_id,
                Document.workspace_id == workspace_id,
                Document.content_hash == content_hash,
            )
        )
        if duplicate:
            raise ServiceError(
                "Document with identical content already exists.",
                status_code=409,
            )

        mime_type = detect_mime_type(filename, content_type)
        document_id = uuid.uuid4()
        storage_key = f"tenants/{context.tenant_id}/documents/{document_id}/{filename}"

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
            raise ServiceError("Document not found.", status_code=404)
        return document

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[Document], int]:
        """List documents belonging to a workspace with pagination."""
        pagination = pagination or PaginationParams()
        ctx = try_current_context()
        if not ctx or not ctx.tenant_id:
            raise ServiceError("Tenant context required", status_code=400)

        stmt = (
            select(Document)
            .where(
                Document.tenant_id == ctx.tenant_id,
                Document.workspace_id == workspace_id,
            )
            .order_by(Document.created_at.desc())
        )
        total = (
            await self.uow.session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            or 0
        )
        items = (
            await self.uow.session.scalars(
                stmt.offset(pagination.offset).limit(pagination.limit)
            )
        ).all()
        return list(items), total

    async def delete(self, document_id: uuid.UUID, storage: StorageProvider) -> None:
        """Delete a document from object storage and the database."""
        document = await self.get(document_id)
        await storage.delete_file(document.storage_key)
        if document.extracted_text_key:
            await storage.delete_file(document.extracted_text_key)
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

        if ext and ext not in EXTENSION_MIME:
            raise ServiceError("Unsupported file type.", status_code=415)
