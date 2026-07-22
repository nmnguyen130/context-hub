from app.core.config import settings
from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult
from app.modules.documents.parsers.base import ParsedBlock


class _PageResolver:
    """Helper class to index and resolve page numbers for text parts."""

    def __init__(self, blocks: list[ParsedBlock] | None) -> None:
        self.text_to_pages: dict[str, set[int]] = {}
        self.page_blocks: list[ParsedBlock] = []

        if blocks:
            for b in blocks:
                if b.page_number is not None:
                    self.page_blocks.append(b)
                    self.text_to_pages.setdefault(b.text.strip(), set()).add(
                        b.page_number
                    )

    def resolve(self, parts: list[str]) -> list[int]:
        """Find matching page numbers for given text parts."""
        if not self.page_blocks:
            return []

        pages: set[int] = set()
        for part in parts:
            stripped = part.strip()
            if stripped in self.text_to_pages:
                pages.update(self.text_to_pages[stripped])
            else:
                for b in self.page_blocks:
                    if b.page_number is not None and (
                        stripped in b.text or b.text in stripped
                    ):
                        pages.add(b.page_number)

        return sorted(pages)


class SlidingWindowChunker(BaseChunker):
    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        self.overlap = overlap or settings.RAG_CHUNK_OVERLAP

    def chunk(
        self, text: str, blocks: list[ParsedBlock] | None = None
    ) -> list[ChunkResult]:
        """Chunk text using a sliding window with paragraph alignment."""
        paragraphs = self._split_paragraphs(text)
        if not paragraphs:
            return []

        page_resolver = _PageResolver(blocks)
        results: list[ChunkResult] = []
        current_parts: list[str] = []
        current_tokens = 0
        char_offset = 0

        for para in paragraphs:
            tokens = self.estimate_tokens(para)
            if current_tokens + tokens > self.chunk_size and current_parts:
                char_offset = self._flush(
                    results, current_parts, char_offset, page_resolver
                )
                current_parts, current_tokens = self._get_overlap(current_parts)

            current_parts.append(para)
            current_tokens += tokens

        if current_parts:
            self._flush(results, current_parts, char_offset, page_resolver)

        return results

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split text into non-empty paragraphs or lines."""
        if not text or not text.strip():
            return []
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paras or [line.strip() for line in text.splitlines() if line.strip()]

    def _get_overlap(self, parts: list[str]) -> tuple[list[str], int]:
        """Extract trailing paragraphs up to overlap token size."""
        if self.overlap <= 0 or not parts:
            return [], 0

        overlap_parts: list[str] = []
        overlap_tokens = 0
        for part in reversed(parts):
            tokens = self.estimate_tokens(part)
            if overlap_tokens + tokens > self.overlap and overlap_parts:
                break
            overlap_parts.append(part)
            overlap_tokens += tokens

        overlap_parts.reverse()
        return overlap_parts, overlap_tokens

    def _flush(
        self,
        results: list[ChunkResult],
        parts: list[str],
        start_offset: int,
        page_resolver: "_PageResolver",
    ) -> int:
        """Create ChunkResult, append to results, and return next char offset."""
        content = "\n\n".join(parts)
        end_offset = start_offset + len(content)

        results.append(
            ChunkResult(
                content=content,
                chunk_index=len(results),
                token_count=self.estimate_tokens(content),
                metadata=ChunkMetadata(
                    page_numbers=page_resolver.resolve(parts),
                    char_start=start_offset,
                    char_end=end_offset,
                    content_type="prose",
                    chunker_used="sliding_window",
                ),
            )
        )
        return end_offset
