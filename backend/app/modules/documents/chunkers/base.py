from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.modules.documents.parsers.base import ParsedBlock


@dataclass
class ChunkMetadata:
    page_numbers: list[int] = field(default_factory=list)
    parent_headers: list[str] = field(default_factory=list)
    char_start: int = 0
    char_end: int = 0
    content_type: str = "prose"
    language: str | None = None
    chunker_used: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class ChunkResult:
    content: str
    chunk_index: int
    token_count: int
    metadata: ChunkMetadata


class BaseChunker(ABC):
    @abstractmethod
    def chunk(
        self, text: str, blocks: list[ParsedBlock] | None = None
    ) -> list[ChunkResult]:
        """Partition text into a list of chunk results."""
        raise NotImplementedError

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Provide a fast, rough token count estimate for the text."""
        return max(1, len(text.split()))
