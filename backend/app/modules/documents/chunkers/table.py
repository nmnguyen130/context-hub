from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult
from app.modules.documents.parsers.base import ParsedBlock


class TableChunker(BaseChunker):
    def chunk(
        self, text: str, blocks: list[ParsedBlock] | None = None
    ) -> list[ChunkResult]:
        """Chunk table blocks from pre-parsed table blocks."""
        if not blocks:
            return []

        table_blocks = [b for b in blocks if b.content_type == "table"]
        return [
            ChunkResult(
                content=b.text,
                chunk_index=idx,
                token_count=self.estimate_tokens(b.text),
                metadata=ChunkMetadata(
                    page_numbers=[b.page_number] if b.page_number is not None else [],
                    content_type="table",
                    chunker_used="table",
                    extra=b.metadata,
                ),
            )
            for idx, b in enumerate(table_blocks)
        ]

