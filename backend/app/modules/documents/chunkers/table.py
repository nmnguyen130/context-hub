"""Table-aware chunker preserving row groups."""

from __future__ import annotations

from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult
from app.modules.documents.parsers.base import ParsedBlock


class TableChunker(BaseChunker):
    MAX_ROWS = 50

    def chunk(self, text: str, blocks: list | None = None) -> list[ChunkResult]:
        if not blocks:
            return []

        table_blocks = [
            b for b in blocks if isinstance(b, ParsedBlock) and b.content_type == "table"
        ]
        if not table_blocks:
            return []

        results: list[ChunkResult] = []
        for idx, block in enumerate(table_blocks):
            results.append(
                ChunkResult(
                    content=block.text,
                    chunk_index=idx,
                    token_count=self.estimate_tokens(block.text),
                    metadata=ChunkMetadata(
                        content_type="table",
                        chunker_used="table",
                        extra=block.metadata,
                    ),
                )
            )
        return results
