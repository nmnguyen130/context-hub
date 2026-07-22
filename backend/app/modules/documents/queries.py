import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.schemas import ScoredChunk


async def update_search_vectors(
    session: AsyncSession,
    chunk_ids: list[uuid.UUID],
    tenant_id: uuid.UUID | None = None,
) -> None:
    """Generate and update full-text search tsvectors in database."""
    if not chunk_ids:
        return

    await session.execute(
        text(
            """
            UPDATE document_chunks
            SET search_vector = to_tsvector('english', content)
            WHERE id = ANY(:ids)
              AND (CAST(:tenant_id AS uuid) IS NULL OR tenant_id = CAST(:tenant_id AS uuid))
            """
        ),
        {"ids": chunk_ids, "tenant_id": tenant_id},
    )


async def dense_search(
    session: AsyncSession,
    embedding: list[float],
    workspace_ids: list[uuid.UUID],
    tenant_id: uuid.UUID | None = None,
    *,
    limit: int = 50,
    ef_search: int = 100,
) -> list[ScoredChunk]:
    """Perform dense similarity search using pgvector with optional tenant isolation."""
    await session.execute(text(f"SET LOCAL hnsw.ef_search = {int(ef_search)}"))
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
    result = await session.execute(
        text(
            """
            SELECT id, document_id, content, metadata,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS cosine_score
            FROM document_chunks
            WHERE (CAST(:tenant_id AS uuid) IS NULL OR tenant_id = CAST(:tenant_id AS uuid))
              AND workspace_id = ANY(:workspace_ids)
              AND is_active = true
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        ),
        {
            "embedding": embedding_str,
            "tenant_id": tenant_id,
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
    session: AsyncSession,
    query: str,
    workspace_ids: list[uuid.UUID],
    tenant_id: uuid.UUID | None = None,
    *,
    limit: int = 50,
) -> list[ScoredChunk]:
    """Perform sparse full-text search using PostgreSQL tsquery with optional tenant isolation."""
    result = await session.execute(
        text(
            """
            SELECT id, document_id, content, metadata,
                   ts_rank_cd(search_vector, websearch_to_tsquery('english', :query)) AS fts_score
            FROM document_chunks
            WHERE (CAST(:tenant_id AS uuid) IS NULL OR tenant_id = CAST(:tenant_id AS uuid))
              AND workspace_id = ANY(:workspace_ids)
              AND is_active = true
              AND search_vector @@ websearch_to_tsquery('english', :query)
            ORDER BY fts_score DESC
            LIMIT :limit
            """
        ),
        {
            "query": query,
            "tenant_id": tenant_id,
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
            fts_score=float(row.fts_score or 0),
        )
        for row in result
    ]
