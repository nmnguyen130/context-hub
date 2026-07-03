import logging
import uuid

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients import GeminiEmbeddingClient
from app.core.config import settings
from app.core.text_utils import normalize_text
from app.modules.documents.models import DocumentChunk
from app.modules.documents.rerankers import get_reranker

logger = logging.getLogger(__name__)


async def retrieve_grounding_chunks(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    query_vector: list[float] | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """
    Modular Retrieval pipeline combining Dense Vector Search, Sparse Keyword Search (FTS),
    Reciprocal Rank Fusion (RRF), Semantic Reranking, and a Corrective Scoring Gate.
    """
    if not query.strip():
        return []

    # Unicode NFC Normalization for Vietnamese query compatibility
    normalized_query = normalize_text(query)

    # 1. Dense Vector Search (skip embedding retrieval if query_vector is precomputed)
    if query_vector is None:
        embedding_client = GeminiEmbeddingClient(client=http_client)
        try:
            query_vector = await embedding_client.get_embedding(normalized_query)
        except Exception as e:
            logger.error(f"Failed to generate embedding for query: {str(e)}")
            query_vector = None

    dense_results = []
    if query_vector is not None:
        # cosine_distance matches <=> operator in pgvector
        dense_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.tenant_id == tenant_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(settings.RAG_LIMIT_DENSE)
        )
        dense_res = await db.execute(dense_stmt)
        dense_results = list(dense_res.scalars().all())

    # 2. Sparse FTS Search (Vietnamese compatible via 'simple' config)
    sparse_query = func.plainto_tsquery(settings.RAG_FTS_LANGUAGE, normalized_query)
    sparse_stmt = (
        select(DocumentChunk)
        .where(
            DocumentChunk.tenant_id == tenant_id,
            DocumentChunk.search_vector.op("@@")(sparse_query),
        )
        .order_by(func.ts_rank_cd(DocumentChunk.search_vector, sparse_query).desc())
        .limit(settings.RAG_LIMIT_SPARSE)
    )
    try:
        sparse_res = await db.execute(sparse_stmt)
        sparse_results = list(sparse_res.scalars().all())
    except Exception as fts_err:
        logger.warning(f"FTS query failed (likely query formatting): {fts_err}")
        sparse_results = []

    # 3. Reciprocal Rank Fusion (RRF) with constant k=60
    k_rrf = 60
    rrf_scores = {}  # Chunk ID -> aggregated score
    chunk_map = {}  # Chunk ID -> DocumentChunk ORM object

    # Accumulate Dense and Sparse ranks
    for results in (dense_results, sparse_results):
        for rank, chunk in enumerate(results):
            chunk_id = chunk.id
            chunk_map[chunk_id] = chunk
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (
                1.0 / (k_rrf + (rank + 1))
            )

    if not rrf_scores:
        return []

    # Sort chunks by RRF score descending
    sorted_chunk_ids = sorted(
        rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
    )
    fused_chunk_ids = sorted_chunk_ids[: settings.RAG_LIMIT_FUSED]

    # Convert chunks to dictionary payloads
    chunks_for_rerank = []
    for cid in fused_chunk_ids:
        chunk = chunk_map[cid]
        chunks_for_rerank.append(
            {
                "id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "tenant_id": str(chunk.tenant_id),
                "content": chunk.content,
                "metadata": chunk.metadata_json,
                "rrf_score": rrf_scores[cid],
            }
        )

    # 4. Semantic Reranking (NoOp/RRF vs Cohere Rerank API)
    reranker = get_reranker(client=http_client)
    reranked_chunks = await reranker.rerank(normalized_query, chunks_for_rerank)

    # 5. Corrective Gate (Filters out chunks below relevance threshold)
    grounding_chunks = []
    for chunk in reranked_chunks:
        score = chunk.get("rerank_score", 0.0)
        if score >= settings.RAG_RELEVANCE_THRESHOLD:
            grounding_chunks.append(chunk)

    return grounding_chunks[: settings.RAG_FINAL_TOP_K]
