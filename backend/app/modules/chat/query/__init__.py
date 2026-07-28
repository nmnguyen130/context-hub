import asyncio
import logging

from dataclasses import dataclass

from app.core.clients import GeminiClient
from app.modules.chat.query.classifier import QueryComplexity, classify_query
from app.modules.chat.query.expander import expand_query
from app.modules.chat.query.hyde import generate_hyde_embedding
from app.modules.chat.query.rewriter import rewrite_query
from app.modules.documents.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QueryPlan:
    queries: list[str]
    embeddings: list[list[float]]
    complexity: QueryComplexity
    rewritten_query: str | None = None


async def prepare_queries(
    query: str,
    history: list[str] | None = None,
    client: GeminiClient | None = None,
    embedder: EmbeddingProvider | None = None,
) -> QueryPlan:
    """Adaptive query understanding pipeline.

    Routes simple/moderate/complex queries through appropriate query transformation steps.
    """
    client = client or GeminiClient()
    embedder = embedder or EmbeddingProvider(client=client)
    history = history or []

    complexity = classify_query(query, history)

    if complexity == QueryComplexity.SIMPLE:
        embedding = await embedder.embed_query(query)
        return QueryPlan(
            queries=[query],
            embeddings=[embedding],
            complexity=complexity,
            rewritten_query=query,
        )

    if complexity == QueryComplexity.MODERATE:
        rewritten = await rewrite_query(query, history, client=client)
        embedding = await embedder.embed_query(rewritten)
        return QueryPlan(
            queries=[rewritten],
            embeddings=[embedding],
            complexity=complexity,
            rewritten_query=rewritten,
        )

    # COMPLEX query: rewrite first, then parallel expand_query + HyDE embedding
    rewritten = await rewrite_query(query, history, client=client)

    async def _safe_hyde() -> list[float] | None:
        try:
            return await generate_hyde_embedding(
                rewritten, client=client, embedder=embedder
            )
        except Exception as exc:
            logger.warning("HyDE embedding generation failed: %s", exc)
            return None

    expanded_res, hyde_emb = await asyncio.gather(
        expand_query(rewritten, client=client, count=3),
        _safe_hyde(),
    )

    all_queries: list[str] = []
    for q in [rewritten] + expanded_res:
        if q not in all_queries:
            all_queries.append(q)

    embeddings = await embedder.embed_texts(all_queries)
    if hyde_emb:
        embeddings.append(hyde_emb)

    return QueryPlan(
        queries=all_queries,
        embeddings=embeddings,
        complexity=complexity,
        rewritten_query=rewritten,
    )


__all__ = [
    "QueryComplexity",
    "QueryPlan",
    "classify_query",
    "rewrite_query",
    "expand_query",
    "generate_hyde_embedding",
    "prepare_queries",
]
