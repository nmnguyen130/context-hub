from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedBlock:
    text: str
    page_number: int | None = None
    heading_level: int | None = None
    content_type: str = "prose"
    metadata: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    blocks: list[ParsedBlock]
    full_text: str
    metadata: dict = field(default_factory=dict)


class BaseParser(ABC):
    @abstractmethod
    def parse(self, data: bytes, filename: str) -> ParseResult:
        """Parse raw file bytes into structured blocks and plain text."""
        raise NotImplementedError
