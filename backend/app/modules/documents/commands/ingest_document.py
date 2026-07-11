# app/modules/documents/commands/ingest_document.py
import io
import logging
import uuid
import sqlalchemy.exc
from sqlalchemy import delete, func, select
from app.core.config import settings
from app.core.database import Database
from app.core.exceptions import ServiceError
from app.core.storage import S3StorageProvider
from app.core.uow import UnitOfWork
from app.core.context import current_context
from app.core.event_bus import event_bus
from app.infrastructure.clients import GeminiEmbeddingClient
from app.modules.documents.chunkers import MarkdownStructureChunker
from app.modules.documents.models import Document, DocumentChunk, Workspace
from app.modules.documents.parsers import parser_registry
from app.modules.documents.repository import DocumentRepository, WorkspaceRepository, DocumentChunkRepository

logger = logging.getLogger(__name__)

_worker_db = None
_worker_storage = None

def get_worker_db() -> Database:
    """Lazy initializer for worker-scoped database engine."""
    global _worker_db
    if _worker_db is None:
        _worker_db = Database(settings.DATABASE_URL)
    return _worker_db

def get_worker_storage():
    """Lazy initializer for worker-scoped storage provider."""
    global _worker_storage
    if _worker_storage is None:
        _worker_storage = S3StorageProvider()
    return _worker_storage

async def run_ingestion(document_id: str) -> None:
    """
    Ingestion Pipeline UseCase.
    Downloads raw document, parses, chunks, generates embeddings, and saves to database.
    """
    db_manager = get_worker_db()
    storage = get_worker_storage()
    context = current_context()

    async with UnitOfWork(
        session_factory=db_manager.session_factory,
        context=context,
        event_bus=event_bus,
        admin_session_factory=db_manager.admin_session_factory,
    ) as uow:
        doc_repo = uow.repo(DocumentRepository)
        doc = await doc_repo.get(uuid.UUID(document_id))
        if not doc:
            raise ServiceError(
                f"Document {document_id} not found in database.", status_code=404
            )

        # 2. Update status to PARSING
        doc.status = "PARSING"
        doc.error_message = None
        await uow.commit()

    # Re-open a fresh UoW for the parsing/chunking work (decoupled transactions)
    async with UnitOfWork(
        session_factory=db_manager.session_factory,
        context=context,
        event_bus=event_bus,
        admin_session_factory=db_manager.admin_session_factory,
    ) as uow:
        doc_repo = uow.repo(DocumentRepository)
        doc = await doc_repo.get(uuid.UUID(document_id))
        if not doc:
            raise ServiceError("Document not found during parsing stage", status_code=404)

        try:
            # 3. Download raw bytes
            content = await storage.download_file(doc.object_store_key)

            # 4. Parse content
            parser = parser_registry.get_parser(doc.name)
            extracted_text = parser.parse(content)

            # 5. Upload parsed plain text
            raw_key_prefix = doc.object_store_key.rsplit("/", 1)[0]
            extracted_key = f"{raw_key_prefix}/extracted.txt"
            extracted_stream = io.BytesIO(extracted_text.encode("utf-8"))
            await storage.upload_file(extracted_stream, extracted_key)

            # 6. Delete existing chunks (idempotency)
            delete_stmt = delete(DocumentChunk).where(
                DocumentChunk.document_id == doc.id
            )
            await uow.session.execute(delete_stmt)

            # 7. Resolve DLP configuration
            dlp_action = settings.RAG_DLP_ACTION
            if doc.workspace_id:
                ws_repo = uow.repo(WorkspaceRepository)
                workspace = await ws_repo.get(doc.workspace_id)
                if workspace:
                    dlp_action = getattr(
                        workspace, "dlp_action", settings.RAG_DLP_ACTION
                    )

            # 8. Generate chunks
            chunker = MarkdownStructureChunker(dlp_action=dlp_action)
            chunks = chunker.chunk_document(extracted_text, doc.name)

            if chunks:
                # 9. Generate embeddings concurrently/batched
                embedding_client = GeminiEmbeddingClient()
                chunk_texts = [c["content"] for c in chunks]
                vectors = []
                for i in range(0, len(chunk_texts), 100):
                    batch = chunk_texts[i : i + 100]
                    batch_vectors = await embedding_client.get_embeddings_batch(batch)
                    vectors.extend(batch_vectors)

                # 10. Save chunks to DB
                chunk_objects = []
                chunk_repo = uow.repo(DocumentChunkRepository)
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

                await chunk_repo.add_all(chunk_objects)

            # 11. Update status to ACTIVE
            doc.status = "ACTIVE"
            await uow.commit()

        except (sqlalchemy.exc.OperationalError, OSError) as infra_err:
            # Bubble up infrastructure errors to Celery for retries
            raise infra_err
        except Exception as logic_err:
            import boto3.exceptions
            import botocore.exceptions

            if isinstance(
                logic_err,
                (botocore.exceptions.BotoCoreError, boto3.exceptions.Boto3Error),
            ):
                raise logic_err

            # Logical exception: mark status as ERROR immediately and commit status change
            doc.status = "ERROR"
            doc.error_message = f"Parsing failed: {str(logic_err)}"[:255]
            await uow.commit()
            raise logic_err

async def mark_document_as_error(document_id: str, error_message: str) -> None:
    """Helper called by worker when retries are exhausted."""
    db_manager = get_worker_db()
    context = current_context()
    async with UnitOfWork(
        session_factory=db_manager.session_factory,
        context=context,
        event_bus=event_bus,
        admin_session_factory=db_manager.admin_session_factory,
    ) as uow:
        doc_repo = uow.repo(DocumentRepository)
        doc = await doc_repo.get(uuid.UUID(document_id))
        if doc:
            doc.status = "ERROR"
            doc.error_message = error_message[:255]
            await uow.commit()
