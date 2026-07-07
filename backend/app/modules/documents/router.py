import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select

from app.api.deps import RAGContainer, get_current_user, get_infra
from app.core.config import settings
from app.core.exceptions import ServiceError
from app.modules.auth.models import User
from app.modules.documents.commands.delete_document import DeleteDocumentCommand
from app.modules.documents.commands.upload_document import UploadDocumentCommand
from app.modules.documents.models import Document
from app.modules.documents.schemas import DocumentResponse

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}


@router.post(
    "/workspaces/{workspace_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    infra: RAGContainer = Depends(get_infra),
    current_user: User = Depends(get_current_user),
) -> Document:
    """Uploads a new document to a workspace.

    Verifies tenant isolation, saves record, uploads raw file, and triggers parsing task.

    Args:
        workspace_id (uuid.UUID): Target workspace ID.
        file (UploadFile): Uploaded file object.
        infra (RAGContainer): Infrastructure registry container.
        current_user (User): Current authenticated user.

    Returns:
        Document: The created Document database model instance.

    Raises:
        ServiceError: If file extension is unsupported or file size exceeds limit.
    """
    # 1. Validate file extension
    filename = file.filename or "unnamed"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ServiceError(
            f"Unsupported file format: '.{ext}'. Supported formats: .pdf, .txt, .md",
            status_code=400,
        )

    # 2. Validate file size
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file.size and file.size > max_size_bytes:
        raise ServiceError(
            f"File size exceeds the limit of {settings.MAX_FILE_SIZE_MB}MB.",
            status_code=400,
        )

    # 3. Delegate to command
    command = UploadDocumentCommand(infra.db, infra.storage)
    doc = await command.execute(
        tenant_id=current_user.tenant_id,
        workspace_id=workspace_id,
        filename=filename,
        file_size=file.size or 0,
        file_obj=file.file,
        mime_type=file.content_type,
    )
    return doc


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    infra: RAGContainer = Depends(get_infra),
    current_user: User = Depends(get_current_user),
) -> Document:
    """Retrieves document status and metadata.

    Enforces multi-tenancy verification.

    Args:
        document_id (uuid.UUID): Target document ID.
        infra (RAGContainer): Infrastructure registry container.
        current_user (User): Current authenticated user.

    Returns:
        Document: The matched Document database model instance.

    Raises:
        ServiceError: If document is not found or belongs to another tenant.
    """
    stmt = select(Document).where(
        Document.id == document_id, Document.tenant_id == current_user.tenant_id
    )
    result = await infra.db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise ServiceError(
            f"Document not found or access denied: {document_id}",
            status_code=404,
        )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    infra: RAGContainer = Depends(get_infra),
    current_user: User = Depends(get_current_user),
) -> None:
    """Deletes the document database record and all associated S3 assets.

    Enforces multi-tenancy verification.

    Args:
        document_id (uuid.UUID): Target document ID to delete.
        infra (RAGContainer): Infrastructure registry container.
        current_user (User): Current authenticated user.
    """
    command = DeleteDocumentCommand(infra.db, infra.storage)
    await command.execute(document_id=document_id, tenant_id=current_user.tenant_id)
