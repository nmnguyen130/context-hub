import re

from app.modules.chat.schemas import CitationDetail
from app.modules.documents.schemas import ScoredChunk

CITATION_PATTERN = re.compile(r"\[\^(\d+)\]")


def extract_citations(
    response_text: str,
    chunks: list[ScoredChunk],
) -> list[CitationDetail]:
    """Parse inline citation markers [^N] from generated text and map them to full chunk metadata."""
    found_indices = sorted(
        {int(match.group(1)) for match in CITATION_PATTERN.finditer(response_text)}
    )

    citations: list[CitationDetail] = []
    for idx in found_indices:
        chunk_idx = idx - 1
        if 0 <= chunk_idx < len(chunks):
            chunk = chunks[chunk_idx]
            doc_name = str(chunk.metadata.get("document_name", "Unknown Document"))
            pages = list(chunk.metadata.get("page_numbers", []))
            excerpt = chunk.content[:200].replace("\n", " ").strip() + "..."

            confidence = float(
                chunk.rerank_score if chunk.rerank_score > 0 else chunk.rrf_score
            )

            citations.append(
                CitationDetail(
                    index=idx,
                    document_id=chunk.document_id,
                    document_name=doc_name,
                    chunk_id=chunk.id,
                    content_excerpt=excerpt,
                    page_numbers=pages,
                    confidence=confidence,
                )
            )

    return citations
