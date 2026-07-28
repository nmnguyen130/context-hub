import uuid

import pytest

from app.modules.chat.grounding.confidence import compute_composite_confidence
from app.modules.chat.grounding.hallucination import check_faithfulness
from app.modules.chat.retrieval.compressor import compress_context, compute_token_budget
from app.modules.chat.retrieval.reranker import context_boost_rerank
from app.modules.documents.schemas import ScoredChunk


@pytest.fixture
def sample_chunks() -> list[ScoredChunk]:
    return [
        ScoredChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content="ContextHub uses logical multi-tenancy sharing a single PostgreSQL database with pgvector.",
            metadata={
                "document_name": "Architecture_Guide.pdf",
                "parent_headers": ["Database Architecture", "Multi-Tenancy"],
            },
            rrf_score=0.03,
        ),
        ScoredChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content="Celery workers process background tasks such as document ingestion and OCR extraction.",
            metadata={
                "document_name": "Celery_Tasks.md",
                "parent_headers": ["Background Processing"],
            },
            rrf_score=0.02,
        ),
    ]


def test_context_boost_rerank(sample_chunks: list[ScoredChunk]) -> None:
    query = "PostgreSQL database multi-tenancy"
    reranked = context_boost_rerank(query, sample_chunks)

    assert len(reranked) == 2
    # First chunk matches query terms in content, document_name, and parent_headers
    assert reranked[0].id == sample_chunks[0].id
    assert reranked[0].rerank_score > sample_chunks[0].rrf_score


def test_compute_token_budget() -> None:
    budget = compute_token_budget(
        "gemini-2.0-flash", system_prompt_tokens=500, history_tokens=1000
    )
    assert 500 <= budget <= 2500


def test_compress_context(sample_chunks: list[ScoredChunk]) -> None:
    query = "multi-tenancy"
    compressed = compress_context(query, sample_chunks, max_tokens=30)

    assert len(compressed) >= 1
    assert len(compressed[0].content.split()) <= 30


def test_check_faithfulness(sample_chunks: list[ScoredChunk]) -> None:
    grounded_response = (
        "ContextHub uses logical multi-tenancy sharing a single PostgreSQL database."
    )
    score, sentence_results = check_faithfulness(grounded_response, sample_chunks)

    assert score >= 0.5
    assert len(sentence_results) == 1
    assert sentence_results[0]["status"] in ("GROUNDED", "PARTIAL")

    ungrounded_response = (
        "The weather in Tokyo is sunny today with a high of 25 degrees."
    )
    score_un, sentence_results_un = check_faithfulness(
        ungrounded_response, sample_chunks
    )

    assert score_un < 0.5
    assert sentence_results_un[0]["status"] == "UNGROUNDED"


def test_compute_composite_confidence() -> None:
    score = compute_composite_confidence(
        retrieval_confidence=0.8,
        faithfulness_score=0.9,
        citation_coverage=0.7,
    )
    assert 0.7 <= score <= 1.0

    cache_score = compute_composite_confidence(0.0, 0.0, 0.0, cache_hit=True)
    assert cache_score == 0.95


def test_compress_context_boundary_sentence_extraction() -> None:
    chunk1 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="First sentence about multi-tenancy. Second sentence explaining PostgreSQL pgvector database details.",
        metadata={},
    )
    chunk2 = ScoredChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="Third sentence focusing on multi-tenancy. Fourth sentence discussing background tasks with Celery workers.",
        metadata={},
    )

    # Budget of 18 tokens fits chunk1 (~12 tokens), but not full chunk2 (~12 tokens).
    # Boundary chunk (chunk2) should be sentence-extracted to fit within headroom.
    compressed = compress_context(
        "multi-tenancy PostgreSQL", [chunk1, chunk2], max_tokens=18
    )
    assert len(compressed) >= 1
    assert any(c.metadata.get("is_compressed") for c in compressed)


def test_compress_context_complexity_adaptive_budget(
    sample_chunks: list[ScoredChunk],
) -> None:
    from app.modules.chat.query.classifier import QueryComplexity

    compressed_simple = compress_context(
        "multi-tenancy",
        sample_chunks,
        max_tokens=100,
        complexity=QueryComplexity.SIMPLE,
    )
    compressed_complex = compress_context(
        "multi-tenancy",
        sample_chunks,
        max_tokens=100,
        complexity=QueryComplexity.COMPLEX,
    )

    # Simple complexity uses 60% budget multiplier, complex uses 100%
    assert len(compressed_simple) <= len(compressed_complex)
