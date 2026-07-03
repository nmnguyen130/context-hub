from abc import ABC, abstractmethod


class DocumentParser(ABC):
    """Abstract interface defining document parsing operations."""

    @abstractmethod
    def parse(self, content: bytes) -> str:
        """Parses document raw content and returns plain text."""
        pass


class TextParser(DocumentParser):
    """Concrete parser for plain text files (.txt, .md)."""

    def parse(self, content: bytes) -> str:
        # Decodes using UTF-8, replacing encoding errors to prevent crashes
        return content.decode("utf-8", errors="replace")


class PDFParser(DocumentParser):
    """Concrete parser for PDF documents using PyMuPDF4LLM for Markdown structure."""

    def parse(self, content: bytes) -> str:
        import pymupdf
        import pymupdf4llm

        # Load PDF directly from memory bytes
        doc = pymupdf.open(stream=content, filetype="pdf")

        # Extract Markdown structure with page chunking
        chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)
        text_parts = [chunk["text"] for chunk in chunks]

        # Combine pages using a clean Page Break character (form feed)
        return "\n\f\n".join(text_parts)


class ParserRegistry:
    """Registry to manage and retrieve document type parsers."""

    def __init__(self):
        self._parsers = {}

    def register(self, extension: str, parser: DocumentParser) -> None:
        """Registers a parser to handle files with the specified extension."""
        self._parsers[extension.lower().strip(".")] = parser

    def get_parser(self, filename: str) -> DocumentParser:
        """Resolves the appropriate parser for a given filename based on its extension."""
        parts = filename.lower().split(".")
        if len(parts) < 2:
            raise ValueError(f"Filename must contain an extension: '{filename}'")

        ext = parts[-1]
        parser = self._parsers.get(ext)
        if not parser:
            raise ValueError(f"Unsupported document format: '.{ext}'")

        return parser


# Create and initialize global parser registry singleton
parser_registry = ParserRegistry()
parser_registry.register("txt", TextParser())
parser_registry.register("md", TextParser())
parser_registry.register("pdf", PDFParser())
