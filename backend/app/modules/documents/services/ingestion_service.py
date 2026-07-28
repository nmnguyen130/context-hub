import io
import logging
import uuid

from sqlalchemy import update

from app.core.uow import UnitOfWork
from app.infrastructure.storage import StorageProvider
from app.modules.documents.chunkers import select_chunks
from app.modules.documents.embeddings import EmbeddingProvider
from app.modules.documents.enrichment import enrich_chunk
from app.modules.documents.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    Workspace,
)
from app.modules.documents.parsers import parse_document
from app.modules.documents.queries import update_search_vectors
from app.modules.documents.security import apply_dlp

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        uow: UnitOfWork,
        storage: StorageProvider,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.uow = uow
        self.storage = storage
        self.embedder = embedder or EmbeddingProvider()

    async def process_document(self, document_id: uuid.UUID) -> None:
        """Orchestrate the ingestion process for a single document."""
        document = await self.uow.session.get(Document, document_id)
        if document is None:
            logger.error("Document %s not found for ingestion", document_id)
            return

        workspace = await self.uow.session.get(Workspace, document.workspace_id)
        if workspace is None:
            document.status = DocumentStatus.ERROR
            document.error_message = "Workspace not found"
            await self.uow.commit()
            return

        try:
            document.status = DocumentStatus.PROCESSING
            await self.uow.flush()

            raw_bytes = await self._download(document.storage_key)
            parsed = parse_document(raw_bytes, document.filename, document.mime_type)

            safe_text, dlp_warnings, _vault = apply_dlp(
                parsed.full_text, workspace.dlp_rules
            )
            if dlp_warnings:
                logger.info(
                    "DLP warnings for document %s: %s", document_id, dlp_warnings
                )

            chunks = select_chunks(safe_text, parsed.blocks)
            if not chunks:
                raise ValueError("No chunks produced from document")

            # Deactivate previous active chunks for this document (soft inactivation for version audit history)
            await self.uow.session.execute(
                update(DocumentChunk)
                .where(
                    DocumentChunk.tenant_id == document.tenant_id,
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.is_active.is_(True),
                )
                .values(is_active=False)
            )

            texts = [c.content for c in chunks]
            embeddings = await self.embedder.embed_texts(texts)

            db_chunks: list[DocumentChunk] = []
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                metadata = enrich_chunk(
                    chunk,
                    document_name=document.filename,
                    workspace_name=workspace.name,
                    file_type=document.mime_type,
                    document_version=document.version,
                )
                db_chunks.append(
                    DocumentChunk(
                        tenant_id=document.tenant_id,
                        document_id=document.id,
                        workspace_id=document.workspace_id,
                        chunk_index=chunk.chunk_index,
                        version=document.version,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        embedding=embedding,
                        metadata_=metadata,
                        is_active=True,
                    )
                )

            self.uow.session.add_all(db_chunks)
            await self.uow.flush()
            chunk_ids = [c.id for c in db_chunks]
            await update_search_vectors(
                self.uow.session, chunk_ids, tenant_id=document.tenant_id
            )

            extracted_key = (
                f"tenants/{document.tenant_id}/documents/{document.id}/extracted.txt"
            )
            await self.storage.upload_file(
                io.BytesIO(safe_text.encode()), extracted_key
            )

            document.extracted_text_key = extracted_key
            document.status = DocumentStatus.ACTIVE
            document.error_message = None
            document.record_event(
                "DOCUMENT_READY",
                {"document_id": str(document.id), "chunk_count": len(db_chunks)},
            )
            await self.uow.commit()
            logger.info(
                "Document %s ingested: %s chunks",
                document_id,
                len(db_chunks),
            )

        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document_id)
            await self.uow.rollback()
            async with self.uow:
                doc = await self.uow.session.get(Document, document_id)
                if doc:
                    doc.status = DocumentStatus.ERROR
                    doc.error_message = str(exc)[:500]
                await self.uow.commit()

    async def _download(self, key: str) -> bytes:
        """Download a file from object storage, combining downloaded chunks."""
        chunks: list[bytes] = []
        async for part in self.storage.download_file(key):
            chunks.append(part)
        return b"".join(chunks)
