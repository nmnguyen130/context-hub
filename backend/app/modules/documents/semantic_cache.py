import logging
import unicodedata
import uuid

import numpy as np

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class SemanticCacheManager:
    """
    Manages semantic caching of user queries and answers in Redis 8
    using native Vector Similarity Search (VSS) / RediSearch.
    """

    def __init__(self):
        self.redis = get_redis_client()
        self.index_name = "idx:semantic_cache"

    async def ensure_index(self) -> None:
        """Ensures that the RediSearch index for vector similarity search exists."""
        try:
            # Query FT.INFO to verify index existence
            await self.redis.execute_command("FT.INFO", self.index_name)
        except Exception:
            logger.info(f"Creating Redis Query Engine index: {self.index_name}")
            try:
                # FT.CREATE commands: HNSW index with COSINE metric on 768-dim float32 vectors
                await self.redis.execute_command(
                    "FT.CREATE",
                    self.index_name,
                    "ON",
                    "HASH",
                    "PREFIX",
                    "1",
                    "semantic_cache:",
                    "SCHEMA",
                    "query_text",
                    "TEXT",
                    "answer",
                    "TEXT",
                    "embedding",
                    "VECTOR",
                    "HNSW",
                    "6",
                    "TYPE",
                    "FLOAT32",
                    "DIM",
                    "768",
                    "DISTANCE_METRIC",
                    "COSINE",
                )
            except Exception as e:
                logger.error(f"Failed to create Redis VSS index: {str(e)}")

    async def get(self, query_embedding: list[float]) -> str | None:
        """
        Retrieves matching answer from semantic cache if similarity is above threshold.
        COSINE distance = 1 - CosineSimilarity. So similarity >= 0.95 is distance <= 0.05.
        """
        if not settings.ENABLE_SEMANTIC_CACHE:
            return None

        # Convert embedding to float32 binary bytes
        vector_bytes = np.array(query_embedding, dtype=np.float32).tobytes()

        # KNN similarity threshold checking: max_distance = 1 - similarity_threshold
        max_distance = 1.0 - settings.SEMANTIC_CACHE_THRESHOLD

        try:
            # FT.SEARCH runs KNN search returning query vector distance as 'score'
            res = await self.redis.execute_command(
                "FT.SEARCH",
                self.index_name,
                "*=>[KNN 1 @embedding $query_vector AS score]",
                "PARAMS",
                "2",
                "query_vector",
                vector_bytes,
                "SORTBY",
                "score",
                "ASC",
                "DIALECT",
                "2",
            )

            data = {}
            if isinstance(res, dict):
                results = res.get(b"results", [])
                if not results:
                    return None
                hit = results[0]
                extra = hit.get(b"extra_attributes", {})
                for k, v in extra.items():
                    key_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                    data[key_str] = v
            elif isinstance(res, list):
                if not res or res[0] == 0:
                    return None
                fields = res[2]
                for i in range(0, len(fields), 2):
                    key_str = (
                        fields[i].decode("utf-8")
                        if isinstance(fields[i], bytes)
                        else str(fields[i])
                    )
                    data[key_str] = fields[i + 1]
            else:
                return None

            score = float(data.get("score", 1.0))
            if score <= max_distance:
                answer = data.get("answer", b"").decode("utf-8")
                logger.info(
                    f"Semantic Cache HIT (distance={score:.4f} <= threshold={max_distance:.4f})"
                )
                return answer

            logger.info(
                f"Semantic Cache MISS (closest hit distance={score:.4f} > threshold={max_distance:.4f})"
            )
            return None

        except Exception as e:
            logger.error(f"Error querying Redis semantic cache: {str(e)}")
            return None

    async def set(
        self, query_text: str, query_embedding: list[float], answer: str
    ) -> None:
        """Saves query text, embedding vector, and answer to Redis with a 7-day TTL."""
        if not settings.ENABLE_SEMANTIC_CACHE:
            return

        normalized_query = unicodedata.normalize("NFC", query_text)
        vector_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
        cache_key = f"semantic_cache:{uuid.uuid4()}"

        try:
            await self.redis.hset(
                cache_key,
                mapping={
                    "query_text": normalized_query.encode("utf-8"),
                    "answer": answer.encode("utf-8"),
                    "embedding": vector_bytes,
                },
            )
            # Expire cache entries in 7 days (604800 seconds)
            await self.redis.expire(cache_key, 7 * 24 * 3600)
            logger.info(
                f"Saved query to Redis semantic cache: {normalized_query[:40]}..."
            )
        except Exception as e:
            logger.error(f"Error saving to Redis semantic cache: {str(e)}")
