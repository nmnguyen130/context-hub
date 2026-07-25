from dataclasses import dataclass, field
from enum import StrEnum


class BlockType(StrEnum):
    """Semantic types for parsed document content blocks."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    CODE = "code"
    LIST = "list"
    IMAGE = "image"
    FORMULA = "formula"


@dataclass(frozen=True, slots=True)
class ContentBlock:
    """Atomic semantic unit extracted from a document."""

    block_type: BlockType
    text: str
    heading_level: int | None = None
    page_number: int | None = None
    language: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Container for the full result of a document parser."""

    blocks: list[ContentBlock]
    full_text: str
    metadata: dict = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """Accurate token count estimator using character-length and word-boundary hybrid heuristic."""
    if not text:
        return 0
    words = text.split()
    if not words:
        return 0

    word_estimate = len(words) * 1.3
    char_estimate = len(text) / 4.0
    return max(1, int((word_estimate + char_estimate) / 2))
