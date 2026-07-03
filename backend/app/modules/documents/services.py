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
    await storage.upload_file(raw_stream, doc.object_store_key)

    # Update DB record with checksum
    doc.checksum = checksum
    await db.commit()
    await db.refresh(doc)

    # Trigger Celery Worker Task dynamically to avoid circular import issues
    from app.worker.tasks import parse_document_task

    parse_document_task.delay(str(doc.id))

    return doc


async def process_document_ingestion(self_task, document_id: str) -> None:
    """
    Service function encapsulating document download, parsing, chunking,
    embedding generation, and storage in the database. Called by Celery worker.
    """

    import boto3
    import botocore.exceptions
    import sqlalchemy.exc
    from sqlalchemy import delete, func, select

    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.core.storage import get_storage_client
    from app.modules.documents.parsers import parser_registry

    # 1. Open DB session with tenant filter disabled for background worker
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Document)
            .where(Document.id == uuid.UUID(document_id))
            .execution_options(skip_tenant_filter=True)
        )
        doc = (await db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found in database.")

        # 2. Update status to PARSING
        doc.status = "PARSING"
        doc.error_message = None
        await db.commit()
        await db.refresh(doc)

        try:
            # 3. Download raw bytes from S3
            storage = get_storage_client()
            content = await storage.download_file(doc.object_store_key)

            # 4. Resolve parser and parse file contents
            parser = parser_registry.get_parser(doc.name)
            extracted_text = parser.parse(content)

            # 5. Upload parsed plain text to S3 (same parent directory)
            raw_key_prefix = doc.object_store_key.rsplit("/", 1)[0]
            extracted_key = f"{raw_key_prefix}/extracted.txt"
            extracted_stream = io.BytesIO(extracted_text.encode("utf-8"))
            await storage.upload_file(extracted_stream, extracted_key)

            # 6. Delete existing chunks if any (idempotency)
            from app.modules.documents.models import DocumentChunk

            delete_stmt = delete(DocumentChunk).where(
                DocumentChunk.document_id == doc.id
            )
            await db.execute(delete_stmt)

            # 7. Generate structural Markdown chunks
            from app.modules.documents.chunkers import MarkdownStructureChunker
            from app.modules.documents.models import Workspace

            dlp_action = settings.RAG_DLP_ACTION
            if doc.workspace_id:
                w_stmt = select(Workspace).where(Workspace.id == doc.workspace_id)
                workspace = (await db.execute(w_stmt)).scalar_one_or_none()
                if workspace:
                    dlp_action = getattr(
                        workspace, "dlp_action", settings.RAG_DLP_ACTION
                    )

            chunker = MarkdownStructureChunker(dlp_action=dlp_action)
            chunks = chunker.chunk_document(extracted_text, doc.name)

            if chunks:
                # 8. Generate embeddings concurrently in batches of 100
                import httpx
                from app.core.clients import GeminiEmbeddingClient

                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    embedding_client = GeminiEmbeddingClient(client=http_client)
                    chunk_texts = [c["content"] for c in chunks]
                    vectors = []
                    for i in range(0, len(chunk_texts), 100):
                        batch = chunk_texts[i : i + 100]
                        batch_vectors = await embedding_client.get_embeddings_batch(
                            batch
                        )
                        vectors.extend(batch_vectors)

                # 9. Save chunks to DB
                chunk_objects = []
                for chunk, vector in zip(chunks, vectors):
                    chunk_obj = DocumentChunk(
                        document_id=doc.id,
                        tenant_id=doc.tenant_id,
                        content=chunk["content"],
                        embedding=vector,
                        search_vector=func.to_tsvector(
                            settings.RAG_FTS_LANGUAGE, chunk["content"]
                        ),
                        metadata_json=chunk["metadata"],
                    )
                    chunk_objects.append(chunk_obj)

                db.add_all(chunk_objects)

            # 10. Update status to ACTIVE
            doc.status = "ACTIVE"
            await db.commit()

        except (
            boto3.exceptions.Boto3Error,
            botocore.exceptions.BotoCoreError,
            sqlalchemy.exc.OperationalError,
            OSError,
        ) as infra_err:
            await db.rollback()
            # Infrastructure exception: request Celery retry with exponential backoff
            retry_count = self_task.request.retries
            countdown = 2**retry_count
            try:
                raise self_task.retry(exc=infra_err, countdown=countdown, max_retries=3)
            except self_task.MaxRetriesExceededError:
                # All retries exhausted: mark document as ERROR
                doc.status = "ERROR"
                doc.error_message = (
                    f"Infrastructure failure (retries exhausted): {str(infra_err)}"[
                        :255
                    ]
                )
                await db.commit()
                raise infra_err

        except Exception as logic_err:
            await db.rollback()
            # Logical exception (unsupported format, corrupt file): mark as ERROR immediately
            doc.status = "ERROR"
            doc.error_message = f"Parsing failed: {str(logic_err)}"[:255]
            await db.commit()
            raise logic_err
