import pytest

from app.modules.documents.semantic_cache import SemanticCacheManager


@pytest.mark.asyncio
async def test_semantic_cache_lifecycle():
    """Verify that we can set, get (similarity check), and miss cached items in Redis."""
    cache = SemanticCacheManager()

    # 1. Initialize VSS index
    await cache.ensure_index()

    # Generate 768-dimensional mock embedding vectors
    query_text = "Mô hình multi-tenancy hoạt động thế nào?"
    query_vector = [0.1] * 768
    cached_answer = "Multi-tenancy chia sẻ 1 DB chung và phân tách bằng tenant_id."

    # 2. Store in cache
    await cache.set(query_text, query_vector, cached_answer)

    # 3. Cache HIT: query with same vector (similarity = 1.0)
    hit_answer = await cache.get(query_vector)
    assert hit_answer == cached_answer

    # 4. Cache HIT: query with highly similar vector (similarity ~ 0.99)
    similar_vector = [0.1] * 768
    similar_vector[0] = 0.1001
    hit_similar = await cache.get(similar_vector)
    assert hit_similar == cached_answer

    # 5. Cache MISS: query with completely different vector (similarity ~ 0.0)
    different_vector = [-0.1] * 768
    miss_answer = await cache.get(different_vector)
    assert miss_answer is None
