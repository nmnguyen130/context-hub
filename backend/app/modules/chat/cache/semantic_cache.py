import json
import logging
import math
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SemanticCache:
    """Redis-backed semantic cache matching user queries by embedding similarity."""

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self.redis = redis_client

    async def get(
        self,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        threshold: float | None = None,
    ) -> dict[str, Any] | None:
        """Check Redis for a semantically similar cached response for the workspace."""
        if not settings.ENABLE_SEMANTIC_CACHE or self.redis is None:
            return None

        threshold = threshold or settings.SEMANTIC_CACHE_THRESHOLD
        pattern = f"semcache:{workspace_id}:*"

        try:
            keys = await self.redis.keys(pattern)
            if not keys:
                return None

            best_similarity = 0.0
            best_cached: dict[str, Any] | None = None

            for key in keys:
                raw_data = await self.redis.get(key)
                if not raw_data:
                    continue

                entry = json.loads(raw_data)
                cached_emb = entry.get("embedding", [])
                sim = cosine_similarity(query_embedding, cached_emb)

                if sim > best_similarity:
                    best_similarity = sim
                    best_cached = entry

            if best_similarity >= threshold and best_cached is not None:
                logger.info(
                    "Semantic cache HIT (similarity: %.4f >= threshold: %.4f)",
                    best_similarity,
                    threshold,
                )
                return {
                    "content": best_cached.get("response", ""),
                    "citations": best_cached.get("citations", []),
                    "similarity": best_similarity,
                }

        except Exception as exc:
            logger.warning("Semantic cache lookup failed: %s", exc)

        return None

    async def set(
        self,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        query_text: str,
        response_text: str,
        citations: list[dict[str, Any]],
        ttl: int | None = None,
    ) -> None:
        """Store a new query embedding and response payload in Redis semantic cache."""
        if not settings.ENABLE_SEMANTIC_CACHE or self.redis is None:
            return

        ttl = ttl or settings.RAG_SEMANTIC_CACHE_TTL
        entry_id = uuid.uuid4().hex[:12]
        key = f"semcache:{workspace_id}:{entry_id}"

        payload = {
            "embedding": query_embedding,
            "query": query_text,
            "response": response_text,
            "citations": citations,
        }

        try:
            await self.redis.setex(key, ttl, json.dumps(payload))
            logger.debug("Stored entry %s in semantic cache (TTL=%s)", key, ttl)
        except Exception as exc:
            logger.warning("Semantic cache set failed: %s", exc)
