import logging
from dataclasses import replace

from app.core.clients import CohereClient
from app.modules.documents.schemas import ScoredChunk

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, cohere_client: CohereClient | None = None) -> None:
        self.client = cohere_client or CohereClient()

    async def rerank(
        self,
        query: str,
        chunks: list[ScoredChunk],
        top_n: int = 10,
    ) -> list[ScoredChunk]:
        """Rerank chunks relative to the query using Cohere Rerank API, with zero-cost fallback."""
        if not chunks:
            return []

        if not self.client.api_key:
            logger.info(
                "COHERE_API_KEY not configured; using RRF scores for reranking fallback."
            )
            return sorted(chunks, key=lambda c: c.rrf_score, reverse=True)[:top_n]

        doc_texts = [c.content for c in chunks]
        try:
            rankings = await self.client.rerank(
                query=query,
                documents=doc_texts,
                top_n=min(top_n, len(chunks)),
            )

            reranked_chunks: list[ScoredChunk] = []
            for original_idx, relevance_score in rankings:
                chunk = chunks[original_idx]
                updated = replace(chunk, rerank_score=float(relevance_score))
                reranked_chunks.append(updated)

            return reranked_chunks
        except Exception as exc:
            logger.warning(
                "Cohere reranking failed: %s. Falling back to RRF sorting.", exc
            )
            return sorted(chunks, key=lambda c: c.rrf_score, reverse=True)[:top_n]
