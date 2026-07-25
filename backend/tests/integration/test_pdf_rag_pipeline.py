import uuid
from pathlib import Path

import pytest

from app.modules.chat.generation.citations import extract_citations
from app.modules.chat.generation.prompts import build_grounded_prompt
from app.modules.chat.query.classifier import QueryComplexity, classify_query
from app.modules.chat.retrieval.fusion import reciprocal_rank_fusion
from app.modules.chat.retrieval.grader import grade_relevance
from app.modules.documents.chunkers import select_chunks
from app.modules.documents.enrichment import enrich_chunk
from app.modules.documents.parsers import parse_pdf
from app.modules.documents.schemas import ScoredChunk
from app.modules.documents.security import apply_dlp


def test_pdf_rag_pipeline_real_cv():
    """Integration test executing the full RAG pipeline against real PDF file: Nguyen_Minh_Nguyen_CV.pdf."""
    pdf_path = Path(__file__).parent.parent / "Nguyen_Minh_Nguyen_CV.pdf"
    assert pdf_path.exists(), f"Target CV PDF not found at {pdf_path}"

    # Step 1: Parse PDF
    pdf_bytes = pdf_path.read_bytes()
    parse_result = parse_pdf(pdf_bytes, filename=pdf_path.name)

    assert len(parse_result.blocks) > 0, "PDF parsing returned 0 blocks"
    assert parse_result.full_text != "", "Parsed full text is empty"

    # Step 2: DLP Security Scanning
    safe_text, dlp_warnings, _ = apply_dlp(parse_result.full_text)
    assert isinstance(safe_text, str)
    assert isinstance(dlp_warnings, list)

    # Step 3: Chunking & Metadata Enrichment
    chunks = select_chunks(safe_text, parse_result.blocks)
    assert len(chunks) > 0, "No chunks generated from PDF text"

    enriched_chunks = []
    for c in chunks:
        meta = enrich_chunk(
            c,
            document_name=pdf_path.name,
            workspace_name="CV Test Workspace",
            file_type="application/pdf",
        )
        assert "topic_tags" in meta
        assert "page_numbers" in meta
        enriched_chunks.append((c, meta))

    # Step 4: Adaptive Query Understanding
    query = "Summarize candidate's technical skills and experience"
    complexity = classify_query(query)
    assert complexity in (
        QueryComplexity.SIMPLE,
        QueryComplexity.MODERATE,
        QueryComplexity.COMPLEX,
    )

    # Step 5: Scoring & Reciprocal Rank Fusion
    scored_chunks = [
        ScoredChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content=c.content,
            metadata={
                "document_name": pdf_path.name,
                "page_numbers": meta.get("page_numbers", [1]),
                "chunk_index": c.chunk_index,
            },
            cosine_score=0.85 - (idx * 0.05),
            fts_score=0.90 - (idx * 0.05),
        )
        for idx, (c, meta) in enumerate(enriched_chunks)
    ]

    fused = reciprocal_rank_fusion([scored_chunks])
    assert len(fused) == len(chunks)

    # Step 6: CRAG Relevance Grading
    grading = grade_relevance(fused, threshold=0.01)
    assert len(grading.accepted) > 0

    # Step 7: Grounded Synthesis & Citation Extraction
    system_prompt, user_prompt = build_grounded_prompt(query, grading.accepted)
    assert pdf_path.name in user_prompt
    assert "[^1]" in user_prompt

    mock_llm_response = f"The candidate has experience in software engineering and cloud infrastructure [^1]."
    citations = extract_citations(mock_llm_response, grading.accepted)
    assert len(citations) == 1
    assert citations[0].document_name == pdf_path.name
