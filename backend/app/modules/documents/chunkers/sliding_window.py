"""Fixed-size sliding window chunker with paragraph alignment."""

from __future__ import annotations

from app.core.config import settings
from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult


class SlidingWindowChunker(BaseChunker):
    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        self.overlap = overlap or settings.RAG_CHUNK_OVERLAP

    def chunk(self, text: str, blocks: list | None = None) -> list[ChunkResult]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        if not paragraphs:
            return []

        results: list[ChunkResult] = []
        current_parts: list[str] = []
        current_tokens = 0
        char_offset = 0
        chunk_index = 0

        def flush() -> None:
            nonlocal chunk_index, char_offset, current_parts, current_tokens
            if not current_parts:
                return
            content = "\n\n".join(current_parts)
            start = char_offset
            end = start + len(content)
            results.append(
                ChunkResult(
                    content=content,
                    chunk_index=chunk_index,
                    token_count=self.estimate_tokens(content),
                    metadata=ChunkMetadata(
                        char_start=start,
                        char_end=end,
                        content_type="prose",
                        chunker_used="sliding_window",
                    ),
                )
            )
            chunk_index += 1
            char_offset = end
            if self.overlap > 0 and current_parts:
                overlap_text = content[-self.overlap * 4 :]
                current_parts = [overlap_text] if overlap_text.strip() else []
                current_tokens = self.estimate_tokens("\n\n".join(current_parts))
            else:
                current_parts = []
                current_tokens = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)
            if current_tokens + para_tokens > self.chunk_size and current_parts:
                flush()
            current_parts.append(para)
            current_tokens += para_tokens

        flush()
        return results
