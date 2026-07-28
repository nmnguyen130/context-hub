import logging
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.chat.models import ChatCacheEntry

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
    """pgvector-backed semantic cache matching user queries by embedding similarity."""

    def __init__(self, threshold: float | None = None) -> None:
        self.default_threshold = threshold

    async def get(
        self,
        session: AsyncSession,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        threshold: float | None = None,
    ) -> dict[str, Any] | None:
        """Query pgvector for a semantically similar cached response for the workspace."""
        if not settings.ENABLE_SEMANTIC_CACHE:
            return None

        threshold = threshold or self.default_threshold or settings.SEMANTIC_CACHE_THRESHOLD
        max_distance = 1.0 - threshold
        now = datetime.now(UTC)

        try:
            dist = ChatCacheEntry.query_embedding.cosine_distance(query_embedding)
            stmt = (
                select(ChatCacheEntry, dist.label("distance"))
                .where(
                    ChatCacheEntry.tenant_id == tenant_id,
                    ChatCacheEntry.workspace_id == workspace_id,
                    ChatCacheEntry.expires_at > now,
                    dist <= max_distance,
                )
                .order_by(dist)
                .limit(1)
            )
            if row := (await session.execute(stmt)).first():
                entry, distance = row
                similarity = 1.0 - float(distance)
                logger.info(
                    "Semantic cache HIT (similarity: %.4f >= threshold: %.4f)",
                    similarity,
                    threshold,
                )
                return {
                    "content": entry.response_text,
                    "citations": entry.citations or [],
                    "similarity": similarity,
                }
        except Exception as exc:
            logger.warning("Semantic cache lookup failed: %s", exc)

        return None

    async def set(
        self,
        session: AsyncSession,
        query_embedding: list[float],
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        query_text: str,
        response_text: str,
        citations: list[dict[str, Any]],
        ttl: int | None = None,
    ) -> None:
        """Store a new query embedding and response payload in pgvector semantic cache."""
        if not settings.ENABLE_SEMANTIC_CACHE:
            return

        expires_at = datetime.now(UTC) + timedelta(
            seconds=ttl or settings.RAG_SEMANTIC_CACHE_TTL
        )
        try:
            entry = ChatCacheEntry(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                query_text=query_text,
                query_embedding=query_embedding,
                response_text=response_text,
                citations=citations,
                expires_at=expires_at,
            )
            session.add(entry)
            await session.flush()
            logger.debug("Stored entry %s in semantic cache", entry.id)
        except Exception as exc:
            logger.warning("Semantic cache set failed: %s", exc)
