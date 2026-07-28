import csv
import hashlib
import io
import mimetypes
import unicodedata
from typing import Callable

from app.modules.documents.parsers.docx import parse_docx
from app.modules.documents.parsers.markdown_scanner import scan_markdown_lines
from app.modules.documents.parsers.pdf import parse_pdf
from app.modules.documents.parsers.types import (
    BlockType,
    ContentBlock,
    ParseResult,
    estimate_tokens,
)


def parse_markdown(data: bytes, filename: str) -> ParseResult:
    """Parse Markdown raw bytes into structured semantic blocks."""
    text = data.decode("utf-8", errors="replace")
    text = unicodedata.normalize("NFC", text)
    blocks = scan_markdown_lines(text.splitlines())
    return ParseResult(
        blocks=blocks,
        full_text=text,
        metadata={"file_type": "text/markdown", "document_name": filename},
    )


def parse_plaintext(data: bytes, filename: str) -> ParseResult:
    """Parse plain text raw bytes into structured paragraph blocks."""
    text = data.decode("utf-8", errors="replace")
    text = unicodedata.normalize("NFC", text)
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    blocks = [
        ContentBlock(
            block_type=BlockType.PARAGRAPH,
            text=" ".join(p.splitlines()).strip(),
        )
        for p in raw_paragraphs
    ]
    return ParseResult(
        blocks=blocks,
        full_text=text,
        metadata={"file_type": "text/plain", "document_name": filename},
    )


def parse_csv(data: bytes, filename: str, batch_size: int = 25) -> ParseResult:
    """Parse CSV raw bytes into grouped table blocks and full text."""
    text = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    schema_hash = hashlib.sha256(",".join(fieldnames).encode()).hexdigest()[:16]

    header = " | ".join(fieldnames)
    separator = " | ".join("---" for _ in fieldnames)

    row_lines = [
        " | ".join(str(row.get(col, "")) for col in fieldnames) for row in reader
    ]

    blocks: list[ContentBlock] = []
    for i in range(0, len(row_lines), batch_size):
        batch = row_lines[i : i + batch_size]
        table_text = f"{header}\n{separator}\n" + "\n".join(batch)
        blocks.append(
            ContentBlock(
                block_type=BlockType.TABLE,
                text=table_text,
                metadata={
                    "column_names": fieldnames,
                    "row_range": [i + 1, i + len(batch)],
                    "schema_hash": schema_hash,
                },
            )
        )

    full_text = unicodedata.normalize("NFC", "\n".join([header] + row_lines))
    return ParseResult(
        blocks=blocks,
        full_text=full_text,
        metadata={"file_type": "text/csv", "document_name": filename},
    )


_PARSER_MAP: dict[str, Callable[[bytes, str], ParseResult]] = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "text/markdown": parse_markdown,
    "text/plain": parse_plaintext,
    "text/csv": parse_csv,
    "application/json": parse_plaintext,
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


def detect_mime_type(filename: str, content_type: str | None = None) -> str:
    """Detect the MIME type of a file based on its extension or provided content type."""
    if content_type and content_type != "application/octet-stream":
        return content_type
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in EXTENSION_MIME:
        return EXTENSION_MIME[ext]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "text/plain"


def parse_document(
    data: bytes, filename: str, content_type: str | None = None
) -> ParseResult:
    """Auto-detect MIME type and parse raw document bytes into a ParseResult."""
    mime = detect_mime_type(filename, content_type)
    parser_fn = _PARSER_MAP.get(mime, parse_plaintext)
    return parser_fn(data, filename)


__all__ = [
    "ContentBlock",
    "BlockType",
    "ParseResult",
    "parse_pdf",
    "parse_docx",
    "parse_markdown",
    "parse_plaintext",
    "parse_csv",
    "detect_mime_type",
    "parse_document",
    "estimate_tokens",
]
