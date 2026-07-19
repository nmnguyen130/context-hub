"""Chunker factory selecting strategy per content type."""

from __future__ import annotations

from app.modules.documents.chunkers.base import ChunkResult
from app.modules.documents.chunkers.code import CodeChunker
from app.modules.documents.chunkers.sliding_window import SlidingWindowChunker
from app.modules.documents.chunkers.structural import StructuralChunker
from app.modules.documents.chunkers.table import TableChunker
from app.modules.documents.parsers.base import ParsedBlock


def select_chunks(text: str, blocks: list[ParsedBlock] | None = None) -> list[ChunkResult]:
    """Choose the cheapest adequate chunking strategy."""
    if blocks:
        has_headings = any(b.content_type == "heading" for b in blocks)
        has_tables = any(b.content_type == "table" for b in blocks)
        has_code = any(b.content_type == "code" for b in blocks)

        if has_tables:
            table_chunks = TableChunker().chunk(text, blocks)
            if table_chunks:
                prose_blocks = [b for b in blocks if b.content_type not in ("table",)]
                prose_text = "\n".join(b.text for b in prose_blocks if b.text.strip())
                other = StructuralChunker().chunk(prose_text, prose_blocks) if has_headings else SlidingWindowChunker().chunk(prose_text)
                return _reindex(table_chunks + other)

        if has_code:
            code_chunks = CodeChunker().chunk(text, blocks)
            if code_chunks:
                return code_chunks

        if has_headings:
            structural = StructuralChunker().chunk(text, blocks)
            if structural:
                return structural

    return SlidingWindowChunker().chunk(text, blocks)


def _reindex(chunks: list[ChunkResult]) -> list[ChunkResult]:
    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i
    return chunks
