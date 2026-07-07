# app/modules/chat/semantic_cache.py
import logging
import struct
import uuid

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.text_utils import normalize_text

logger = logging.getLogger(__name__)


class SemanticCacheManager:
    """Manages semantic caching of user queries and answers in Redis.

    Uses native Vector Similarity Search (VSS) / RediSearch.
    Provides tenant-scoped caching to prevent cross-tenant data leaks.
    """

    _index_ensured: bool = False

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis = (
            redis_client
            if redis_client is not None
            else aioredis.from_url(settings.REDIS_URL, decode_responses=False)
        )
        self.index_name = "idx:semantic_cache"

    async def ensure_index(self) -> None:
        """Ensures that the RediSearch index for vector similarity search exists."""
        if SemanticCacheManager._index_ensured:
            return

        try:
            # Query FT.INFO to verify index existence
            await self.redis.execute_command("FT.INFO", self.index_name)
            SemanticCacheManager._index_ensured = True
        except Exception:
            logger.info(f"Creating Redis Query Engine index: {self.index_name}")
            try:
                from app.modules.documents.models import DocumentChunk

                dim = str(DocumentChunk.embedding.type.dim)

                # FT.CREATE commands: HNSW index with COSINE metric on float32 vectors, including tenant_id as TAG
                await self.redis.execute_command(
                    "FT.CREATE",
                    self.index_name,
                    "ON",
                    "HASH",
                    "PREFIX",
                    "1",
                    "semantic_cache:",
                    "SCHEMA",
                    "tenant_id",
                    "TAG",
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
                    dim,
                    "DISTANCE_METRIC",
                    "COSINE",
                )
                SemanticCacheManager._index_ensured = True
            except Exception as e:
                logger.error(f"Failed to create Redis VSS index: {str(e)}")

    async def get(
        self, tenant_id: uuid.UUID, query_embedding: list[float]
    ) -> str | None:
        """
        Retrieves matching answer from semantic cache if similarity is above threshold.
        COSINE distance = 1 - CosineSimilarity. So similarity >= 0.95 is distance <= 0.05.
        Strictly scopes lookup to the current tenant to prevent cross-tenant data leaks.
        """
        if not settings.ENABLE_SEMANTIC_CACHE:
            return None

        await self.ensure_index()

        # Convert embedding to float32 binary bytes using Python's built-in struct
        vector_bytes = struct.pack(f"<{len(query_embedding)}f", *query_embedding)

        # KNN similarity threshold checking: max_distance = 1 - similarity_threshold
        max_distance = 1.0 - settings.SEMANTIC_CACHE_THRESHOLD

        tenant_tag = str(tenant_id).replace("-", "")

        try:
            # FT.SEARCH runs KNN search scoped by tenant_id TAG, returning query vector distance as 'score'
            res = await self.redis.execute_command(
                "FT.SEARCH",
                self.index_name,
                f"@tenant_id:{{{tenant_tag}}}=>[KNN 1 @embedding $query_vector AS score]",
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
                    f"Semantic Cache HIT (distance={score:.4f} <= threshold={max_distance:.4f}) for tenant {tenant_id}"
                )
                return answer

            logger.info(
                f"Semantic Cache MISS (closest hit distance={score:.4f} > threshold={max_distance:.4f}) for tenant {tenant_id}"
            )
            return None

        except Exception as e:
            logger.error(f"Error querying Redis semantic cache: {str(e)}")
            return None

    async def set(
        self,
        tenant_id: uuid.UUID,
        query_text: str,
        query_embedding: list[float],
        answer: str,
    ) -> None:
        """Saves query text, tenant scope, embedding vector, and answer to Redis with a 7-day TTL."""
        if not settings.ENABLE_SEMANTIC_CACHE:
            return

        await self.ensure_index()

        normalized_query = normalize_text(query_text)
        vector_bytes = struct.pack(f"<{len(query_embedding)}f", *query_embedding)
        cache_key = f"semantic_cache:{str(tenant_id)}:{uuid.uuid4()}"
        tenant_tag = str(tenant_id).replace("-", "")

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(
                    cache_key,
                    mapping={
                        "tenant_id": tenant_tag,
                        "query_text": normalized_query.encode("utf-8"),
                        "answer": answer.encode("utf-8"),
                        "embedding": vector_bytes,
                    },
                )
                pipe.expire(cache_key, 7 * 24 * 3600)
                await pipe.execute()
            logger.info(
                f"Saved query to Redis semantic cache for tenant {tenant_id}: {normalized_query[:40]}..."
            )
        except Exception as e:
            logger.error(f"Error saving to Redis semantic cache: {str(e)}")
