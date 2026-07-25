from dataclasses import dataclass, field

from app.core.clients import GeminiClient
from app.modules.chat.query.classifier import QueryComplexity, classify_query
from app.modules.chat.query.expander import expand_query
from app.modules.chat.query.hyde import generate_hyde_embedding
from app.modules.chat.query.rewriter import rewrite_query
from app.modules.documents.embeddings import EmbeddingProvider


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

    # COMPLEX query: rewrite + multi-query expansion + HyDE
    rewritten = await rewrite_query(query, history, client=client)
    expanded = await expand_query(rewritten, client=client, count=3)

    # Combine rewritten and expanded queries (deduplicated)
    all_queries: list[str] = []
    for q in [rewritten] + expanded:
        if q not in all_queries:
            all_queries.append(q)

    embeddings = await embedder.embed_texts(all_queries)

    # HyDE embedding generation
    try:
        hyde_emb = await generate_hyde_embedding(
            rewritten, client=client, embedder=embedder
        )
        embeddings.append(hyde_emb)
    except Exception:
        pass  # Non-fatal if HyDE fails

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
