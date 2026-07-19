"""Heading-aware structural chunker."""

from __future__ import annotations

from app.core.config import settings
from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult
from app.modules.documents.chunkers.sliding_window import SlidingWindowChunker
from app.modules.documents.parsers.base import ParsedBlock


class StructuralChunker(BaseChunker):
    def __init__(self, max_size: int | None = None) -> None:
        self.max_size = max_size or settings.RAG_CHUNK_SIZE * 2
        self.fallback = SlidingWindowChunker()

    def chunk(self, text: str, blocks: list | None = None) -> list[ChunkResult]:
        if not blocks:
            return self.fallback.chunk(text)

        sections: list[tuple[list[str], list[str], list[int]]] = []
        headers: list[str] = []
        current_lines: list[str] = []
        page_numbers: list[int] = []

        for block in blocks:
            if isinstance(block, ParsedBlock) and block.content_type == "heading":
                if current_lines:
                    sections.append((list(headers), current_lines, list(page_numbers)))
                    current_lines = []
                    page_numbers = []
                if block.heading_level and block.heading_level <= len(headers):
                    headers = headers[: block.heading_level - 1]
                headers.append(block.text)
            else:
                line = block.text if isinstance(block, ParsedBlock) else str(block)
                current_lines.append(line)
                if isinstance(block, ParsedBlock) and block.page_number:
                    page_numbers.append(block.page_number)

        if current_lines:
            sections.append((list(headers), current_lines, list(page_numbers)))

        results: list[ChunkResult] = []
        chunk_index = 0
        char_offset = 0

        for section_headers, lines, pages in sections:
            content = "\n".join(lines)
            token_count = self.estimate_tokens(content)
            if token_count > self.max_size:
                sub_chunks = self.fallback.chunk(content)
                for sub in sub_chunks:
                    sub.chunk_index = chunk_index
                    sub.metadata.parent_headers = section_headers
                    sub.metadata.page_numbers = sorted(set(pages))
                    sub.metadata.chunker_used = "structural"
                    sub.metadata.char_start = char_offset
                    char_offset = sub.metadata.char_end = char_offset + len(sub.content)
                    results.append(sub)
                    chunk_index += 1
            else:
                end = char_offset + len(content)
                results.append(
                    ChunkResult(
                        content=content,
                        chunk_index=chunk_index,
                        token_count=token_count,
                        metadata=ChunkMetadata(
                            page_numbers=sorted(set(pages)),
                            parent_headers=section_headers,
                            char_start=char_offset,
                            char_end=end,
                            content_type="prose",
                            chunker_used="structural",
                        ),
                    )
                )
                char_offset = end
                chunk_index += 1

        return results or self.fallback.chunk(text)
