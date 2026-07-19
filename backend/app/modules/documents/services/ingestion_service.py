"""Document ingestion orchestrator."""

from __future__ import annotations

import io
import logging
import uuid

from app.core.uow import UnitOfWork
from app.modules.documents.chunkers import select_chunks
from app.modules.documents.embeddings import EmbeddingProvider
from app.modules.documents.enrichment import enrich_chunk
from app.modules.documents.models import Document, DocumentChunk, DocumentStatus, Workspace
from app.modules.documents.parsers import parse_document
from app.modules.documents.repository import DocumentRepository, update_search_vectors
from app.modules.documents.security import apply_dlp

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        uow: UnitOfWork,
        storage,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.uow = uow
        self.storage = storage
        self.embedder = embedder or EmbeddingProvider()
        self.repo = DocumentRepository(uow.session)

    async def process_document(self, document_id: uuid.UUID) -> None:
        document = await self.uow.session.get(Document, document_id)
        if document is None:
            logger.error("Document %s not found for ingestion", document_id)
            return

        workspace = await self.uow.session.get(Workspace, document.workspace_id)
        if workspace is None:
            await self.repo.update_document_status(
                document_id, DocumentStatus.ERROR, "Workspace not found"
            )
            await self.uow.commit()
            return

        try:
            document.status = DocumentStatus.PROCESSING
            await self.uow.flush()

            raw_bytes = await self._download(document.storage_key)
            parsed = parse_document(raw_bytes, document.filename, document.mime_type)

            safe_text, dlp_warnings, _vault = apply_dlp(parsed.full_text, workspace.dlp_rules)
            if dlp_warnings:
                logger.info("DLP warnings for document %s: %s", document_id, dlp_warnings)


            chunks = select_chunks(safe_text, parsed.blocks)
            if not chunks:
                raise ValueError("No chunks produced from document")

            await self.repo.deactivate_chunks(document_id)

            texts = [c.content for c in chunks]
            embeddings = await self.embedder.embed_texts(texts)

            db_chunks: list[DocumentChunk] = []
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                metadata = enrich_chunk(
                    chunk,
                    document_name=document.filename,
                    workspace_name=workspace.name,
                    file_type=document.mime_type,
                )
                db_chunks.append(
                    DocumentChunk(
                        tenant_id=document.tenant_id,
                        document_id=document.id,
                        workspace_id=document.workspace_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        embedding=embedding,
                        metadata_=metadata,
                    )
                )

            chunk_ids = await self.repo.bulk_insert_chunks(db_chunks)
            await update_search_vectors(self.uow.session, chunk_ids)

            extracted_key = (
                f"tenants/{document.tenant_id}/documents/{document.id}/extracted.txt"
            )
            await self.storage.upload_file(io.BytesIO(safe_text.encode()), extracted_key)

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
                await self.repo.update_document_status(
                    document_id, DocumentStatus.ERROR, str(exc)[:500]
                )
                await self.uow.commit()

    async def _download(self, key: str) -> bytes:
        chunks: list[bytes] = []
        async for part in self.storage.download_file(key):
            chunks.append(part)
        return b"".join(chunks)
