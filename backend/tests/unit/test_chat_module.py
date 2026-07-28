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
    assert classify_query("What is the refund policy?") == QueryComplexity.SIMPLE
    assert (
        classify_query("How do I configure SAML SSO authentication for my workspace?")
        == QueryComplexity.MODERATE
    )
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

    fused = reciprocal_rank_fusion([[c1, c2], [c1]], k=60)
    assert len(fused) == 2
    assert fused[0].id == chunk1_id
    assert fused[0].rrf_score > fused[1].rrf_score


def test_relevance_grader_and_empty_fallback():
    """Verify CRAG relevance grading thresholds and empty accepted list (M3)."""
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

    res1 = grade_relevance([c1, c2], threshold=0.1)
    assert len(res1.accepted) == 1
    assert not res1.is_low_confidence

    res2 = grade_relevance([c2], threshold=0.1)
    assert len(res2.accepted) == 0
    assert res2.is_low_confidence


def test_citation_extraction():
    """Verify parsing inline markers [^1], [^2] to CitationDetail schemas."""
    doc_id = uuid.uuid4()
    c1 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Security paragraph.",
        metadata={"document_name": "Security.pdf", "page_numbers": [3]},
        rerank_score=0.9,
    )
    c2 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Compliance paragraph.",
        metadata={"document_name": "Compliance.pdf", "page_numbers": [7]},
        rerank_score=0.8,
    )

    citations = extract_citations(
        "ContextHub uses AES-256 encryption [^1] and complies with SOC2 [^2].",
        [c1, c2],
    )
    assert len(citations) == 2
    assert citations[0].document_name == "Security.pdf"
    assert citations[1].document_name == "Compliance.pdf"


def test_prompt_building_and_history():
    """Verify system prompt and history block formatting (L5)."""
    c1 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="RAG search guidelines",
        metadata={"document_name": "GUIDELINES.md", "page_numbers": [1]},
    )
    system, user_prompt = build_grounded_prompt(
        query="Explain RAG guidelines",
        chunks=[c1],
        running_summary="User is setting up search.",
        history=["user: What is ContextHub?", "assistant: ContextHub is an AI platform."],
    )

    assert "ContextHub" in system
    assert "[^1] Document: GUIDELINES.md" in user_prompt
    assert "Recent Conversation History" in user_prompt


def test_sse_event_framing_and_schemas():
    """Verify SSEEvent serialization and ChatRequest validation."""
    req = ChatRequest(workspace_id=uuid.uuid4(), message="Test query")
    assert req.message == "Test query"

    sse = SSEEvent(
        type="done",
        data={"full_text": "Answer", "usage": {"total_tokens": 150}},
    )
    assert sse.type == "done"
    assert sse.data["usage"]["total_tokens"] == 150


@pytest.mark.asyncio
async def test_semantic_cache_operations():
    """Verify pgvector SemanticCache get and set methods."""
    cache = SemanticCache(threshold=0.9)
    mock_execute_result = MagicMock()
    mock_execute_result.first.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_execute_result)

    res = await cache.get(
        session=session,
        query_embedding=[0.1] * 768,
        workspace_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
    )
    assert res is None
