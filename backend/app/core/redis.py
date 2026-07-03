import redis.asyncio as aioredis

from app.core.config import settings

_redis_client = None


def get_redis_client() -> aioredis.Redis:
    """Gets a singleton async Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=False,  # Keep binary safe for embedding vectors
        )
    return _redis_client
