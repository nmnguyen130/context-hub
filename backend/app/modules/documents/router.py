# app/modules/documents/router.py
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from app.api.deps import RAGContainer, get_current_user, get_infra, get_uow
from app.core.config import settings
from app.core.exceptions import ServiceError
from app.core.uow import UnitOfWork
from app.modules.auth.models import User
from app.modules.documents.commands.delete_document import DeleteDocumentCommand
from app.modules.documents.commands.upload_document import UploadDocumentCommand
from app.modules.documents.models import Document
from app.modules.documents.repository import DocumentRepository
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
    uow: UnitOfWork = Depends(get_uow),
) -> Document:
    """Uploads a new document to a workspace."""
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
    command = UploadDocumentCommand(uow, infra.storage)
    doc = await command.execute(
        tenant_id=current_user.tenant_id,
        workspace_id=workspace_id,
        filename=filename,
        file_size=file.size or 0,
        file_obj=file.file,
        mime_type=file.content_type,
    )
    await uow.commit()
    return doc

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> Document:
    """Retrieves document status and metadata."""
    doc = await uow.repo(DocumentRepository).get(document_id)
    if not doc or doc.tenant_id != current_user.tenant_id:
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
    uow: UnitOfWork = Depends(get_uow),
) -> None:
    """Deletes the document database record and all associated S3 assets."""
    command = DeleteDocumentCommand(uow, infra.storage)
    await command.execute(document_id=document_id, tenant_id=current_user.tenant_id)
    await uow.commit()
