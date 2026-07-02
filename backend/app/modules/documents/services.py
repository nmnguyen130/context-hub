import hashlib
import io
import uuid
from typing import BinaryIO

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageProvider
from app.modules.documents.models import Document, Workspace


async def create_document_record(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    workspace_id: uuid.UUID,
    filename: str,
    file_size: int,
    mime_type: str | None = None,
) -> Document:
    """
    Creates a PENDING Document record in the database.
    Verifies that the parent Workspace belongs to the requesting tenant.
    """
    # 1. Enforce Logical Multi-Tenancy check on parent Workspace
    workspace_stmt = select(Workspace).where(
        Workspace.id == workspace_id, Workspace.tenant_id == tenant_id
    )
    workspace_res = await db.execute(workspace_stmt)
    workspace = workspace_res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied.",
        )

    # 2. Extract file extension
    parts = filename.split(".")
    ext = parts[-1].lower() if len(parts) > 1 else "bin"

    # 3. Create document ID and compute key path: s3://bucket/tenant_id/workspace_id/doc_id/raw.ext
    doc_id = uuid.uuid4()
    object_store_key = f"{str(tenant_id)}/{str(workspace_id)}/{str(doc_id)}/raw.{ext}"

    # 4. Insert Document
    doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        name=filename,
        file_type=ext,
        object_store_key=object_store_key,
        status="PENDING",
        file_size=file_size,
        mime_type=mime_type,
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def process_document_upload(
    db: AsyncSession, doc: Document, file_obj: BinaryIO, storage: StorageProvider
) -> Document:
    """
    Computes checksum, uploads the raw file to object storage,
    and triggers the asynchronous parsing task.
    """
    # Read bytes for checksum and S3 upload
    content = file_obj.read()

    # Compute SHA256 Checksum
    checksum = hashlib.sha256(content).hexdigest()

    # Upload raw file payload to S3
    raw_stream = io.BytesIO(content)
    storage.upload_file(raw_stream, doc.object_store_key)

    # Update DB record with checksum
    doc.checksum = checksum
    await db.commit()
    await db.refresh(doc)

    # Trigger Celery Worker Task dynamically to avoid circular import issues
    from app.worker.tasks import parse_document_task

    parse_document_task.delay(str(doc.id))

    return doc
