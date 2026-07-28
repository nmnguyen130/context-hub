import logging
from dataclasses import replace

from app.core.clients import CohereClient
from app.modules.documents.schemas import ScoredChunk
from app.modules.chat.text_utils import tokenize as _tokenize

logger = logging.getLogger(__name__)


def context_boost_rerank(query: str, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
    """Rerank chunks using CPU-based term overlap and metadata scoring."""
    if not chunks:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return chunks

    boosted = []
    for chunk in chunks:
        content_tokens = _tokenize(chunk.content)
        intersection = query_tokens & content_tokens
        union = query_tokens | content_tokens
        jaccard = len(intersection) / max(len(union), 1)

        headers = chunk.metadata.get("parent_headers") or chunk.metadata.get("heading_trail") or []
        headers_text = " ".join(str(h) for h in headers) if isinstance(headers, list | tuple) else str(headers)
        heading_bonus = 0.15 if query_tokens & _tokenize(headers_text) else 0.0

        doc_name = str(chunk.metadata.get("document_name", ""))
        filename_bonus = 0.10 if query_tokens & _tokenize(doc_name) else 0.0

        base_score = chunk.rrf_score if chunk.rrf_score > 0 else chunk.cosine_score
        score = base_score + (jaccard * 0.35) + heading_bonus + filename_bonus
        boosted.append(replace(chunk, rerank_score=float(score)))

    return sorted(boosted, key=lambda c: c.rerank_score, reverse=True)


class CohereReranker:
    """Rerank chunks using Cohere API."""

    def __init__(self, cohere_client: CohereClient | None = None) -> None:
        self.client = cohere_client or CohereClient()

    async def rerank(
        self,
        query: str,
        chunks: list[ScoredChunk],
        top_n: int = 10,
    ) -> list[ScoredChunk]:
        """Execute Cohere rerank API call."""
        if not chunks or not self.client.api_key:
            return chunks[:top_n]

        doc_texts = [c.content for c in chunks]
        try:
            rankings = await self.client.rerank(
                query=query,
                documents=doc_texts,
                top_n=min(top_n, len(chunks)),
            )

            reranked = []
            for original_idx, relevance_score in rankings:
                chunk = chunks[original_idx]
                reranked.append(replace(chunk, rerank_score=float(relevance_score)))

            return reranked
        except Exception as exc:
            logger.warning("Cohere reranking API call failed: %s", exc)
            return chunks[:top_n]


class Reranker:
    """Unified reranking orchestrator."""

    def __init__(self, cohere_client: CohereClient | None = None) -> None:
        self.cohere_reranker = CohereReranker(cohere_client=cohere_client)

    async def rerank(
        self,
        query: str,
        chunks: list[ScoredChunk],
        top_n: int = 10,
        use_cohere: bool = False,
    ) -> list[ScoredChunk]:
        """Rerank chunks using ContextBoost CPU or Cohere API."""
        if not chunks:
            return []

        cpu_reranked = context_boost_rerank(query, chunks)
        if not use_cohere or not self.cohere_reranker.client.api_key:
            return cpu_reranked[:top_n]

        return await self.cohere_reranker.rerank(
            query=query,
            chunks=cpu_reranked,
            top_n=top_n,
        )
