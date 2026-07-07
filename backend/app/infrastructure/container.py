from sqlalchemy.ext.asyncio import AsyncSession


class RAGContainer:
    """Unified container for database, redis, and storage infrastructure."""

    def __init__(self, db: AsyncSession, redis, storage) -> None:
        self.db = db
        self.redis = redis
        self.storage = storage

    def get_embedding_client(self, provider: str = "gemini"):
        from app.infrastructure.clients import get_embedding_client

        return get_embedding_client(provider)

    def get_chat_client(self, provider: str = "gemini"):
        from app.infrastructure.clients import get_chat_client

        return get_chat_client(provider)

    def get_reranker(self, provider: str = "context_boost"):
        from app.infrastructure.clients import get_reranker

        return get_reranker(provider)

    def get_cache(self):
        from app.modules.chat.semantic_cache import SemanticCacheManager

        return SemanticCacheManager(self.redis)
