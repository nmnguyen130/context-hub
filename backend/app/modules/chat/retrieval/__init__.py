import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.chat.query import QueryPlan
from app.modules.chat.retrieval.fusion import reciprocal_rank_fusion
from app.modules.chat.retrieval.grader import GradingResult, grade_relevance
from app.modules.chat.retrieval.reranker import Reranker
from app.modules.documents.queries import dense_search, sparse_search
from app.modules.documents.schemas import ScoredChunk


@dataclass(slots=True)
class RetrievalResult:
    chunks: list[ScoredChunk]
    confidence: float
    needs_retry: bool
    grading: GradingResult


async def retrieve_context(
    query_plan: QueryPlan,
    workspace_ids: list[uuid.UUID],
    tenant_id: uuid.UUID,
    session: AsyncSession,
    reranker: Reranker | None = None,
    original_query: str | None = None,
) -> RetrievalResult:
    """Execute hybrid dense + sparse retrieval, RRF fusion, reranking, and CRAG relevance grading."""
    reranker = reranker or Reranker()
    original_query = original_query or (
        query_plan.queries[0] if query_plan.queries else ""
    )

    all_dense_results: list[list[ScoredChunk]] = []
    all_sparse_results: list[list[ScoredChunk]] = []

    # 1. Parallel dense + sparse searches for each query/embedding pair in plan
    for query_text, embedding in zip(
        query_plan.queries, query_plan.embeddings, strict=False
    ):
        dense_res = await dense_search(
            session=session,
            embedding=embedding,
            workspace_ids=workspace_ids,
            tenant_id=tenant_id,
            limit=50,
        )
        sparse_res = await sparse_search(
            session=session,
            query=query_text,
            workspace_ids=workspace_ids,
            tenant_id=tenant_id,
            limit=50,
        )
        if dense_res:
            all_dense_results.append(dense_res)
        if sparse_res:
            all_sparse_results.append(sparse_res)

    result_sets = all_dense_results + all_sparse_results
    if not result_sets:
        grading = grade_relevance([], threshold=settings.RAG_RELEVANCE_THRESHOLD)
        return RetrievalResult(
            chunks=[],
            confidence=0.0,
            needs_retry=True,
            grading=grading,
        )

    # 2. Reciprocal Rank Fusion (RRF)
    fused_chunks = reciprocal_rank_fusion(result_sets, k=settings.RAG_RRF_K)

    # 3. Reranking
    top_candidates = fused_chunks[: settings.RAG_FINAL_TOP_K * 3]
    reranked_chunks = await reranker.rerank(
        query=original_query,
        chunks=top_candidates,
        top_n=settings.RAG_FINAL_TOP_K * 2,
    )

    # 4. Relevance grading (CRAG)
    grading = grade_relevance(
        reranked_chunks, threshold=settings.RAG_RELEVANCE_THRESHOLD
    )

    final_chunks = grading.accepted[: settings.RAG_FINAL_TOP_K]

    return RetrievalResult(
        chunks=final_chunks,
        confidence=grading.avg_confidence,
        needs_retry=grading.is_low_confidence,
        grading=grading,
    )


__all__ = [
    "Reranker",
    "GradingResult",
    "RetrievalResult",
    "grade_relevance",
    "reciprocal_rank_fusion",
    "retrieve_context",
]
