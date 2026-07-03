import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import get_storage_client
from app.modules.auth.models import User
from app.modules.documents.models import Document
from app.modules.documents.schemas import DocumentResponse
from app.modules.documents.services import (
    create_document_record,
    process_document_upload,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/workspaces/{workspace_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a new document to a workspace.
    Verifies tenant isolation, saves record in PENDING state,
    uploads raw file to S3, triggers parsing task, and returns 202 Accepted.
    """
    # 1. Validate file extension
    filename = file.filename or "unnamed"
    parts = filename.split(".")
    ext = parts[-1].lower() if len(parts) > 1 else ""
    if ext not in ["pdf", "txt", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: '.{ext}'. Supported formats: .pdf, .txt, .md",
        )

    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file.size and file.size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the limit of {settings.MAX_FILE_SIZE_MB}MB.",
        )

    # 2. Create database record in PENDING state
    # Enforces multi-tenancy bounds internally on Workspace
    doc_record = await create_document_record(
        db=db,
        tenant_id=current_user.tenant_id,
        workspace_id=workspace_id,
        filename=filename,
        file_size=file.size or 0,
        mime_type=file.content_type,
    )

    # 3. Stream upload payload to S3 and dispatch background worker task
    storage_client = get_storage_client()
    try:
        updated_doc = await process_document_upload(
            db=db, doc=doc_record, file_obj=file.file, storage=storage_client
        )
        return updated_doc
    except Exception as e:
        # If upload fails, mark status as ERROR in DB to keep records consistent
        doc_record.status = "ERROR"
        doc_record.error_message = f"Upload failed: {str(e)}"
        db.add(doc_record)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document upload: {str(e)}",
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves document status and metadata.
    Enforces multi-tenancy verification.
    """
    stmt = select(Document).where(
        Document.id == document_id, Document.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes the document database record and all associated files from S3.
    Enforces multi-tenancy verification.
    """
    stmt = select(Document).where(
        Document.id == document_id, Document.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    # 1. Delete associated raw and parsed assets from S3
    storage_client = get_storage_client()

    # Delete raw file
    try:
        await storage_client.delete_file(doc.object_store_key)
    except Exception:
        pass  # Ignore missing files on S3 to prevent locking deletes

    # Delete extracted text file (same parent S3 folder)
    try:
        raw_key_prefix = doc.object_store_key.rsplit("/", 1)[0]
        extracted_key = f"{raw_key_prefix}/extracted.txt"
        await storage_client.delete_file(extracted_key)
    except Exception:
        pass

    # 2. Delete database record
    await db.delete(doc)
    await db.commit()
