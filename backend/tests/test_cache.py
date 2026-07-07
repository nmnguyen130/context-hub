import uuid

import pytest

from app.modules.chat.semantic_cache import SemanticCacheManager


@pytest.mark.asyncio
async def test_semantic_cache_lifecycle():
    """Verify that we can set, get (similarity check), and miss cached items in Redis with tenant isolation."""
    cache = SemanticCacheManager()

    # Flush Redis to guarantee test isolation
    await cache.redis.flushdb()

    # 1. Initialize VSS index
    await cache.ensure_index()

    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # Generate 768-dimensional mock embedding vectors
    query_text = "Mô hình multi-tenancy hoạt động thế nào?"
    query_vector = [0.1] * 768
    cached_answer = "Multi-tenancy chia sẻ 1 DB chung và phân tách bằng tenant_id."

    # 2. Store in cache for tenant_a
    await cache.set(tenant_a, query_text, query_vector, cached_answer)

    # 3. Cache HIT: query with same vector (similarity = 1.0) under tenant_a context
    hit_answer = await cache.get(tenant_a, query_vector)
    assert hit_answer == cached_answer

    # 4. Cache MISS: query with same vector under tenant_b context (Tenant isolation check)
    isolated_answer = await cache.get(tenant_b, query_vector)
    assert isolated_answer is None

    # 5. Cache HIT: query with highly similar vector (similarity ~ 0.99) under tenant_a context
    similar_vector = [0.1] * 768
    similar_vector[0] = 0.1001
    hit_similar = await cache.get(tenant_a, similar_vector)
    assert hit_similar == cached_answer

    # 6. Cache MISS: query with completely different vector (similarity ~ 0.0) under tenant_a context
    different_vector = [-0.1] * 768
    miss_answer = await cache.get(tenant_a, different_vector)
    assert miss_answer is None
