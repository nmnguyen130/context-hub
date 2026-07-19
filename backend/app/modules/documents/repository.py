"""Database access for document chunks and search."""

from __future__ import annotations

import uuid
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models import Document, DocumentChunk, DocumentStatus
from app.modules.documents.schemas import ScoredChunk


async def update_search_vectors(session: AsyncSession, chunk_ids: list[uuid.UUID]) -> None:
    """Generate and update full-text search tsvectors in database."""
    if not chunk_ids:
        return
    await session.execute(
        text(
            """
            UPDATE document_chunks
            SET search_vector = to_tsvector('english', content)
            WHERE id = ANY(:ids)
            """
        ),
        {"ids": chunk_ids},
    )


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        return await self.session.get(Document, document_id)

    async def deactivate_chunks(self, document_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

    async def bulk_insert_chunks(self, chunks: list[DocumentChunk]) -> list[uuid.UUID]:
        self.session.add_all(chunks)
        await self.session.flush()
        return [c.id for c in chunks]

    async def count_workspace_chunks(self, workspace_id: uuid.UUID) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(DocumentChunk)
                .where(
                    DocumentChunk.workspace_id == workspace_id,
                    DocumentChunk.is_active.is_(True),
                )
            )
            or 0
        )

    async def dense_search(
        self,
        embedding: list[float],
        workspace_ids: list[uuid.UUID],
        *,
        limit: int = 50,
        ef_search: int = 100,
    ) -> list[ScoredChunk]:
        await self.session.execute(
            text("SET LOCAL hnsw.ef_search = :ef"),
            {"ef": ef_search},
        )
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        result = await self.session.execute(
            text(
                """
                SELECT id, document_id, content, metadata,
                       1 - (embedding <=> :embedding::vector) AS cosine_score
                FROM document_chunks
                WHERE workspace_id = ANY(:workspace_ids)
                  AND is_active = true
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> :embedding::vector
                LIMIT :limit
                """
            ),
            {
                "embedding": embedding_str,
                "workspace_ids": workspace_ids,
                "limit": limit,
            },
        )
        return [
            ScoredChunk(
                id=row.id,
                document_id=row.document_id,
                content=row.content,
                metadata=row.metadata or {},
                cosine_score=float(row.cosine_score or 0),
            )
            for row in result
        ]

    async def sparse_search(
        self,
        query: str,
        workspace_ids: list[uuid.UUID],
        *,
        limit: int = 50,
    ) -> list[ScoredChunk]:
        result = await self.session.execute(
            text(
                """
                SELECT id, document_id, content, metadata,
                       ts_rank_cd(search_vector, websearch_to_tsquery('english', :query)) AS fts_score
                FROM document_chunks
                WHERE workspace_id = ANY(:workspace_ids)
                  AND is_active = true
                  AND search_vector @@ websearch_to_tsquery('english', :query)
                ORDER BY fts_score DESC
                LIMIT :limit
                """
            ),
            {"query": query, "workspace_ids": workspace_ids, "limit": limit},
        )
        return [
            ScoredChunk(
                id=row.id,
                document_id=row.document_id,
                content=row.content,
                metadata=row.metadata or {},
                fts_score=float(row.fts_score or 0),
            )
            for row in result
        ]

    async def update_document_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> None:
        doc = await self.session.get(Document, document_id)
        if doc:
            doc.status = status
            doc.error_message = error_message
