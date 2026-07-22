from app.core.config import settings
from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult
from app.modules.documents.chunkers.sliding_window import SlidingWindowChunker
from app.modules.documents.parsers.base import ParsedBlock


class StructuralChunker(BaseChunker):
    def __init__(self, max_size: int | None = None) -> None:
        self.max_size = max_size or settings.RAG_CHUNK_SIZE * 2
        self.fallback = SlidingWindowChunker()

    def chunk(
        self, text: str, blocks: list[ParsedBlock] | None = None
    ) -> list[ChunkResult]:
        """Chunk text structurally based on heading blocks."""
        if not blocks:
            return self.fallback.chunk(text)

        sections = self._parse_sections(blocks)
        if not sections:
            return self.fallback.chunk(text, blocks)

        results: list[ChunkResult] = []
        char_offset = 0

        for headers, lines, pages in sections:
            content = "\n".join(lines)
            token_count = self.estimate_tokens(content)

            if token_count > self.max_size:
                sub_chunks = self.fallback.chunk(content, blocks)
                for sub in sub_chunks:
                    sub.chunk_index = len(results)
                    sub.metadata.parent_headers = headers
                    sub.metadata.chunker_used = "structural"
                    sub.metadata.char_start = char_offset
                    sub.metadata.char_end = char_offset + len(sub.content)
                    char_offset = sub.metadata.char_end
                    results.append(sub)
            else:
                end = char_offset + len(content)
                results.append(
                    ChunkResult(
                        content=content,
                        chunk_index=len(results),
                        token_count=token_count,
                        metadata=ChunkMetadata(
                            page_numbers=sorted(pages),
                            parent_headers=headers,
                            char_start=char_offset,
                            char_end=end,
                            content_type="prose",
                            chunker_used="structural",
                        ),
                    )
                )
                char_offset = end

        return results or self.fallback.chunk(text, blocks)

    @staticmethod
    def _parse_sections(
        blocks: list[ParsedBlock],
    ) -> list[tuple[list[str], list[str], set[int]]]:
        """Group blocks into sections based on heading hierarchy."""
        sections: list[tuple[list[str], list[str], set[int]]] = []
        headers: list[str] = []
        current_lines: list[str] = []
        page_numbers: set[int] = set()

        for block in blocks:
            if block.content_type == "heading":
                if current_lines:
                    sections.append((list(headers), current_lines, set(page_numbers)))
                    current_lines = []
                    page_numbers = set()
                if block.heading_level and block.heading_level <= len(headers):
                    headers = headers[: block.heading_level - 1]
                headers.append(block.text)
            else:
                current_lines.append(block.text)

            if block.page_number is not None:
                page_numbers.add(block.page_number)

        if current_lines:
            sections.append((list(headers), current_lines, set(page_numbers)))

        return sections

