"""Conditional Hypothetical Document Embedding."""

from __future__ import annotations

from app.core.clients import GeminiClient
from app.modules.documents.embeddings import EmbeddingProvider


async def generate_hyde_embedding(
    query: str,
    *,
    client: GeminiClient | None = None,
    embedder: EmbeddingProvider | None = None,
) -> list[float]:
    client = client or GeminiClient()
    embedder = embedder or EmbeddingProvider(client=client)
    hypothetical = await client.generate(
        f"Write a concise factual paragraph that would answer: {query}",
        temperature=0.2,
    )
    return await embedder.embed_query(hypothetical)
