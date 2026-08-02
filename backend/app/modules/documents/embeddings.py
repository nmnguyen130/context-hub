import asyncio
import logging
import math
import random

from app.core.clients import GeminiClient
from app.core.config import settings
from app.core.exceptions import ServiceError

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
MAX_RETRIES = 3


def l2_normalize(vector: list[float]) -> list[float]:
    """Normalize a vector to unit length using L2 norm."""
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def validate_dimension(vector: list[float]) -> list[float]:
    """Validate the embedding dimension and apply L2 normalization."""
    expected = settings.RAG_EMBEDDING_DIMENSION
    if len(vector) != expected:
        raise ServiceError(
            f"Embedding dimension mismatch: expected {expected}, got {len(vector)}",
            status_code=503,
        )
    return l2_normalize(vector)


class EmbeddingProvider:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client or GeminiClient()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of text strings in batches."""
        if not texts:
            return []

        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            try:
                vectors = await self._embed_batch_with_retry(batch, i // BATCH_SIZE)
                all_vectors.extend(vectors)
            except Exception:
                logger.error("Failed embedding batch starting at index %s", i)
                raise
        return all_vectors

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        vectors = await self.embed_texts([query])
        return vectors[0]

    async def _embed_batch_with_retry(
        self, batch: list[str], batch_idx: int
    ) -> list[list[float]]:
        """Embed a single batch of text strings with exponential backoff retry."""
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                raw = await self.client.embed(batch, model=settings.RAG_EMBEDDING_MODEL)
                return [validate_dimension(v) for v in raw]
            except Exception as exc:
                last_error = exc
                delay = (2**attempt) + random.random()
                logger.warning(
                    "Embedding batch %s failed (attempt %s): %s",
                    batch_idx,
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(delay)

        raise ServiceError(
            f"Embedding failed for batch {batch_idx} after {MAX_RETRIES} retries. "
            f"Last error: {last_error}",
            status_code=503,
        )
