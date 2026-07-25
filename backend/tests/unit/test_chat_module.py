import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.chat.cache.semantic_cache import SemanticCache, cosine_similarity
from app.modules.chat.generation.citations import extract_citations
from app.modules.chat.generation.prompts import build_grounded_prompt
from app.modules.chat.query.classifier import QueryComplexity, classify_query
from app.modules.chat.retrieval.fusion import reciprocal_rank_fusion
from app.modules.chat.retrieval.grader import grade_relevance
from app.modules.chat.schemas import ChatRequest, CitationDetail, SSEEvent
from app.modules.documents.schemas import ScoredChunk


def test_query_classifier():
    """Verify adaptive query complexity classification."""
    # Simple query
    assert classify_query("What is the refund policy?") == QueryComplexity.SIMPLE

    # Moderate query with question and moderate length
    assert (
        classify_query("How do I configure SAML SSO authentication for my workspace?")
        == QueryComplexity.MODERATE
    )

    # Complex query with comparison and multi-hop triggers
    assert (
        classify_query(
            "Compare document chunking strategies versus sliding window and then summarize the key differences based on performance."
        )
        == QueryComplexity.COMPLEX
    )


def test_reciprocal_rank_fusion():
    """Verify RRF correctly combines ranked lists."""
    chunk1_id = uuid.uuid4()
    chunk2_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    c1 = ScoredChunk(id=chunk1_id, document_id=doc_id, content="Text 1", metadata={})
    c2 = ScoredChunk(id=chunk2_id, document_id=doc_id, content="Text 2", metadata={})

    # Set 1: c1 ranked first (rank 1), c2 ranked second (rank 2)
    set1 = [c1, c2]
    # Set 2: c1 ranked first (rank 1)
    set2 = [c1]

    fused = reciprocal_rank_fusion([set1, set2], k=60)
    assert len(fused) == 2
    assert fused[0].id == chunk1_id
    assert fused[0].rrf_score > fused[1].rrf_score


def test_relevance_grader():
    """Verify CRAG relevance grading thresholds."""
    c1 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="Relevant chunk",
        metadata={},
        rerank_score=0.85,
    )
    c2 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="Irrelevant chunk",
        metadata={},
        rerank_score=0.01,
    )

    result = grade_relevance([c1, c2], threshold=0.1)
    assert len(result.accepted) == 1
    assert result.accepted[0].id == c1.id
    assert len(result.rejected) == 1
    assert not result.is_low_confidence


def test_citation_extraction():
    """Verify parsing inline markers [^1], [^2] to CitationDetail schemas."""
    chunk1_id = uuid.uuid4()
    chunk2_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    c1 = ScoredChunk(
        id=chunk1_id,
        document_id=doc_id,
        content="First paragraph about security.",
        metadata={"document_name": "Security.pdf", "page_numbers": [3]},
        rerank_score=0.9,
    )
    c2 = ScoredChunk(
        id=chunk2_id,
        document_id=doc_id,
        content="Second paragraph about compliance.",
        metadata={"document_name": "Compliance.pdf", "page_numbers": [7, 8]},
        rerank_score=0.8,
    )

    llm_output = "ContextHub uses AES-256 encryption [^1] and complies with SOC2 [^2]."
    citations = extract_citations(llm_output, [c1, c2])

    assert len(citations) == 2
    assert citations[0].index == 1
    assert citations[0].document_name == "Security.pdf"
    assert citations[0].page_numbers == [3]
    assert citations[1].index == 2
    assert citations[1].document_name == "Compliance.pdf"


def test_prompt_building():
    """Verify system prompt and context document formatting."""
    c1 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="RAG search guidelines",
        metadata={"document_name": "GUIDELINES.md", "page_numbers": [1]},
    )
    system, user_prompt = build_grounded_prompt(
        query="Explain RAG guidelines",
        chunks=[c1],
        running_summary="User is setting up enterprise search.",
    )

    assert "ContextHub" in system
    assert "[^1] Document: GUIDELINES.md" in user_prompt
    assert "User is setting up enterprise search" in user_prompt
    assert "Explain RAG guidelines" in user_prompt


def test_cosine_similarity():
    """Verify vector cosine similarity calculation."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-5
    assert abs(cosine_similarity(v1, v3) - 0.0) < 1e-5


@pytest.mark.asyncio
async def test_semantic_cache_operations():
    """Verify semantic cache set and get operations."""
    mock_redis = AsyncMock()
    cache = SemanticCache(redis_client=mock_redis)

    workspace_id = uuid.uuid4()
    query_emb = [0.5, 0.5, 0.0]

    # Test cache set
    await cache.set(
        query_embedding=query_emb,
        workspace_id=workspace_id,
        query_text="What is RAG?",
        response_text="RAG stands for Retrieval-Augmented Generation.",
        citations=[],
    )
    assert mock_redis.setex.called

    # Test cache miss when no keys exist
    mock_redis.keys.return_value = []
    res = await cache.get(query_emb, workspace_id)
    assert res is None


def test_schemas_validation():
    """Verify Pydantic schema serialization."""
    req = ChatRequest(
        workspace_id=uuid.uuid4(),
        message="Test user query",
    )
    assert req.message == "Test user query"
    assert req.session_id is None

    sse = SSEEvent(type="token", data={"text": "Hello"})
    assert sse.type == "token"
    assert sse.data == {"text": "Hello"}
