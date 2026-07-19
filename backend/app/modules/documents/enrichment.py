"""Metadata enrichment for document chunks."""

from __future__ import annotations

import re
from collections import Counter

from app.modules.documents.chunkers.base import ChunkResult


def extract_topic_tags(text: str, top_n: int = 5) -> list[str]:
    """Extract top frequent words as topic tags, skipping stopwords."""
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stopwords = {
        "that",
        "this",
        "with",
        "from",
        "have",
        "will",
        "been",
        "were",
        "they",
        "their",
        "about",
        "which",
        "when",
        "where",
        "there",
        "these",
        "those",
        "would",
        "could",
        "should",
        "into",
        "also",
        "than",
        "then",
        "some",
        "such",
        "only",
        "other",
        "more",
        "most",
        "very",
        "just",
        "your",
        "what",
        "each",
    }
    filtered = [w for w in words if w not in stopwords]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def enrich_chunk(
    chunk: ChunkResult,
    *,
    document_name: str,
    workspace_name: str,
    file_type: str,
) -> dict:
    """Enrich chunk metadata with document-level context and topic tags."""
    meta = chunk.metadata
    return {
        "page_numbers": meta.page_numbers,
        "parent_headers": meta.parent_headers,
        "char_start": meta.char_start,
        "char_end": meta.char_end,
        "content_type": meta.content_type,
        "language": meta.language,
        "chunker_used": meta.chunker_used,
        "topic_tags": extract_topic_tags(chunk.content),
        "document_name": document_name,
        "workspace_name": workspace_name,
        "file_type": file_type,
        **meta.extra,
    }
