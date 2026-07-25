from app.modules.documents.chunkers.assembler import DocumentAssembler
from app.modules.documents.chunkers.types import Chunk, ChunkMetadata
from app.modules.documents.parsers.types import ContentBlock


def select_chunks(
    text: str,
    blocks: list[ContentBlock] | None = None,
    section_break_level: int = 3,
) -> list[Chunk]:
    """Select and execute the optimal chunking strategy maintaining natural document order."""
    assembler = DocumentAssembler(section_break_level=section_break_level)
    return assembler.chunk_document(text, blocks)


__all__ = [
    "select_chunks",
    "DocumentAssembler",
    "Chunk",
    "ChunkMetadata",
]
