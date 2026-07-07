import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings
from app.infrastructure.clients import CohereRerankClient

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    """Abstract interface defining the document reranking step."""

    @abstractmethod
    async def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """
        Reranks a list of retrieved chunk dictionaries for a given query string.
        Appends a 'rerank_score' key to each chunk dictionary and sorts descending.
        """
        pass


class NoOpReranker(BaseReranker):
    """Pass-through reranker ($0 cost) that preserves original RRF ranks."""

    async def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            # Assign dummy scores decreasing from 1.0 down to 0.0 based on RRF order
            chunk["rerank_score"] = 1.0 - (idx / total) if total > 0 else 1.0
        return chunks


class CohereReranker(BaseReranker):
    """Concrete reranker invoking Cohere's multi-lingual reranking endpoint."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = CohereRerankClient(client=client)

    async def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        if not chunks:
            return []

        documents = [chunk["content"] for chunk in chunks]

        try:
            results = await self.client.rerank(query, documents)

            # Map the returned relevance scores back to the original chunks
            # Cohere results list: [{"index": int, "relevance_score": float}, ...]
            for result in results:
                idx = result["index"]
                if 0 <= idx < len(chunks):
                    chunks[idx]["rerank_score"] = float(result["relevance_score"])

            # Sort chunks by relevance score in descending order
            chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return chunks

        except Exception as e:
            logger.error(
                f"Cohere Reranker failed: {str(e)}. Falling back to No-Op (RRF) ranking."
            )
            fallback = NoOpReranker()
            return await fallback.rerank(query, chunks)


class ContextBoostReranker(BaseReranker):
    """
    Zero-cost algorithmic reranker.
    Calculates a relevance boost based on query term overlap with chunk metadata
    (section_title and document_name), refined by Jaccard lexical similarity on text.
    """

    async def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        query_words = set(query.lower().split())
        if not query_words or not chunks:
            return chunks

        max_rrf = max((c.get("rrf_score", 0.0) for c in chunks), default=0.0)
        rrf_scale = max_rrf if max_rrf > 0.0 else 1.0

        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            section_title = str(metadata.get("section_title", "")).lower()
            doc_name = str(metadata.get("document_name", "")).lower()

            # Calculate word overlaps
            section_words = set(section_title.split())
            doc_words = set(doc_name.split())

            section_overlap = (
                len(query_words.intersection(section_words)) / len(query_words)
                if query_words
                else 0.0
            )
            doc_overlap = (
                len(query_words.intersection(doc_words)) / len(query_words)
                if query_words
                else 0.0
            )

            # Lexical Jaccard overlap on chunk text content (zero cost token check)
            content_words = set(chunk["content"].lower().split())
            content_jaccard = (
                len(query_words.intersection(content_words))
                / len(query_words.union(content_words))
                if query_words
                else 0.0
            )

            # Compute boost factor
            boost = (
                (section_overlap * 0.4) + (doc_overlap * 0.2) + (content_jaccard * 0.4)
            )

            # Final rerank score merges normalized RRF rank with the boost (weighted combination)
            normalized_rrf = chunk.get("rrf_score", 0.0) / rrf_scale
            chunk["rerank_score"] = (normalized_rrf * 0.6) + (boost * 0.4)

        # Sort descending by new score
        chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return chunks


def get_reranker(client: httpx.AsyncClient | None = None) -> BaseReranker:
    """Factory resolver for Reranker instances based on configuration settings."""
    provider = settings.RAG_RERANK_PROVIDER.lower().strip()
    if provider == "cohere":
        return CohereReranker(client=client)
    elif provider == "context_boost":
        return ContextBoostReranker()
    return NoOpReranker()
