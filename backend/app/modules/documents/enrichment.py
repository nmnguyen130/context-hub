import re
from collections import Counter

from app.modules.documents.chunkers.types import Chunk

STOPWORDS = frozenset(
    {
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
)


def extract_topic_tags(text: str, top_n: int = 5) -> list[str]:
    """Extract top frequent words as topic tags, skipping stopwords."""
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def enrich_chunk(
    chunk: Chunk,
    *,
    document_name: str,
    workspace_name: str,
    file_type: str,
    document_version: int = 1,
) -> dict:
    """Enrich chunk metadata with document-level context, versioning, and topic tags."""
    meta = chunk.metadata
    heading_trail_list = list(meta.heading_trail)
    return {
        "page_numbers": list(meta.page_numbers),
        "heading_trail": heading_trail_list,
        "parent_headers": heading_trail_list,
        "char_start": meta.char_start,
        "char_end": meta.char_end,
        "content_type": meta.content_type,
        "language": meta.language,
        "topic_tags": extract_topic_tags(chunk.content),
        "document_name": document_name,
        "workspace_name": workspace_name,
        "file_type": file_type,
        "document_version": document_version,
        **meta.extra,
    }
