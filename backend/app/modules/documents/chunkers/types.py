from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Rich metadata attributes associated with a document chunk."""

    page_numbers: tuple[int, ...] = field(default_factory=tuple)
    heading_trail: tuple[str, ...] = field(default_factory=tuple)
    char_start: int = 0
    char_end: int = 0
    content_type: str = "prose"
    language: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Chunk:
    """Container representing a single chunk ready for vector embedding."""

    content: str
    chunk_index: int
    token_count: int
    metadata: ChunkMetadata
