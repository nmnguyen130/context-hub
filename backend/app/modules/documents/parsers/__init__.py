import mimetypes

from app.modules.documents.parsers.base import BaseParser, ParseResult
from app.modules.documents.parsers.csv import CSVParser
from app.modules.documents.parsers.docx import DocxParser
from app.modules.documents.parsers.markdown import MarkdownParser
from app.modules.documents.parsers.pdf import PDFParser
from app.modules.documents.parsers.plaintext import PlaintextParser

PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    "application/pdf": PDFParser,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser,
    "text/markdown": MarkdownParser,
    "text/plain": PlaintextParser,
    "text/csv": CSVParser,
    "application/json": PlaintextParser,
}

EXTENSION_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".log": "text/plain",
}


def detect_mime_type(filename: str, content_type: str | None) -> str:
    """Detect the MIME type of a file based on its extension or provided content type."""
    if content_type and content_type != "application/octet-stream":
        return content_type
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in EXTENSION_MIME:
        return EXTENSION_MIME[ext]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "text/plain"


def get_parser(mime_type: str) -> BaseParser:
    """Get the appropriate parser instance from the registry for the given MIME type."""
    parser_cls = PARSER_REGISTRY.get(mime_type, PlaintextParser)
    return parser_cls()


def parse_document(
    data: bytes, filename: str, content_type: str | None = None
) -> ParseResult:
    """Auto-detect MIME type and parse raw document bytes into a ParseResult."""
    mime = detect_mime_type(filename, content_type)
    parser = get_parser(mime)
    return parser.parse(data, filename)
