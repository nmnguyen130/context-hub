from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.chat.retrieval import retrieve_grounding_chunks
from app.modules.documents.models import Document, DocumentChunk, Workspace
from app.modules.tenant.models import Tenant


@pytest.mark.asyncio
async def test_vietnamese_hybrid_search_retrieval(db: AsyncSession):
    """
    Integration test for Vietnamese Hybrid Search (Dense + Sparse).
    Validates RRF rank merging, simple stemming, and relevance threshold filtering.
    """
    # 1. Setup Tenant and Workspace
    tenant = Tenant(name="FTS Tenant", plan_tier="FREE")
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    workspace = Workspace(name="FTS Workspace", tenant_id=tenant.id)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    # 2. Setup Document
    doc = Document(
        name="fts_test.md",
        file_type="md",
        object_store_key=f"{tenant.id}/{workspace.id}/fts_test/raw.md",
        status="ACTIVE",
        file_size=1024,
        mime_type="text/markdown",
        tenant_id=tenant.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 3. Create Document Chunks
    # Vector dimensions = 768. Matching query vector is [0.1] * 768.
    chunk_a = DocumentChunk(
        document_id=doc.id,
        tenant_id=tenant.id,
        content="Thiết kế hệ thống database multi-tenancy phân tách dữ liệu bằng tenant_id.",
        embedding=[0.1] * 768,
        metadata_json={"page_number": 1, "document_name": doc.name},
    )
    chunk_b = DocumentChunk(
        document_id=doc.id,
        tenant_id=tenant.id,
        content="Cách cài đặt Celery worker kết nối qua Redis broker trong Python.",
        embedding=[-0.1] * 768,
        metadata_json={"page_number": 2, "document_name": doc.name},
    )

    # Manually populate search_vector using Postgres to_tsvector with 'simple' config
    from sqlalchemy import func

    chunk_a.search_vector = func.to_tsvector("simple", chunk_a.content)
    chunk_b.search_vector = func.to_tsvector("simple", chunk_b.content)

    db.add_all([chunk_a, chunk_b])
    await db.commit()

    # 4. Mock Gemini Embedding client to return [0.1] * 768 for our query
    with patch(
        "app.infrastructure.clients.GeminiEmbeddingClient.get_embedding",
        return_value=[0.1] * 768,
    ):
        # Query 1: Keywords matching chunk_a exactly (FTS trigger + Dense match)
        results = await retrieve_grounding_chunks(
            db, tenant.id, "database multi-tenancy"
        )
        assert len(results) >= 1
        assert "multi-tenancy" in results[0]["content"]
        assert results[0]["metadata"]["page_number"] == 1

        # Query 2: Keywords matching chunk_b exactly (Sparse match only, different dense vector)
        results_b = await retrieve_grounding_chunks(
            db, tenant.id, "Celery worker Redis"
        )
        assert len(results_b) >= 1
        assert "Celery worker" in results_b[0]["content"]
        assert results_b[0]["metadata"]["page_number"] == 2

        # Query 3: Non-matching query (relevance threshold gate triggers)
        with patch.object(settings, "RAG_RELEVANCE_THRESHOLD", 0.99):

            class LowScoreReranker:
                async def rerank(self, query, chunks):
                    for c in chunks:
                        c["rerank_score"] = 0.1
                    return chunks

            with patch(
                "app.modules.chat.retrieval.get_reranker",
                return_value=LowScoreReranker(),
            ):
                results_gated = await retrieve_grounding_chunks(
                    db, tenant.id, "Không liên quan gì cả"
                )
                # Should be empty since score is 0.1 < 0.99
                assert len(results_gated) == 0


@pytest.mark.asyncio
async def test_context_boost_reranker():
    """Verify that ContextBoostReranker ranks metadata-matching chunks higher at zero cost."""
    from app.modules.chat.rerankers import ContextBoostReranker

    reranker = ContextBoostReranker()
    query = "database schema design"

    chunks = [
        {
            "content": "This chunk describes background tasks in Python.",
            "rrf_score": 0.5,
            "metadata": {
                "section_title": "Celery Workers",
                "document_name": "worker.pdf",
            },
        },
        {
            "content": "This chunk details how multi-tenancy database schemas are partitioned.",
            "rrf_score": 0.4,  # Lower RRF score initially
            "metadata": {
                "section_title": "Database Schema",
                "document_name": "database.pdf",
            },
        },
    ]

    reranked = await reranker.rerank(query, chunks)

    # The second chunk matches the query keywords in both section_title and document_name
    # So its score should be boosted above the first chunk's score
    assert len(reranked) == 2
    assert "multi-tenancy database" in reranked[0]["content"]
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]
