import io
import unicodedata
from typing import Iterator

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.modules.documents.parsers.types import BlockType, ContentBlock, ParseResult


def _iter_block_items(doc: DocxDocument) -> Iterator[Paragraph | Table]:
    """Yield each paragraph and table child in sequential document body order."""
    body_elm = doc.element.body
    for child in body_elm.iterchildren():
        if child.tag.endswith("p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("tbl"):
            yield Table(child, doc)


def parse_docx(data: bytes, filename: str) -> ParseResult:
    """Parse DOCX raw bytes into structured headings, tables, and prose blocks in document order."""
    doc = DocxDocument(io.BytesIO(data))
    blocks: list[ContentBlock] = []
    lines: list[str] = []
    table_count = 0

    current_paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal current_paragraph_lines
        if current_paragraph_lines:
            text_content = " ".join(current_paragraph_lines).strip()
            if text_content:
                blocks.append(
                    ContentBlock(
                        block_type=BlockType.PARAGRAPH,
                        text=text_content,
                    )
                )
            current_paragraph_lines = []

    for item in _iter_block_items(doc):
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text:
                flush_paragraph()
                continue
            lines.append(text)
            style = (item.style.name or "").lower() if item.style else ""

            if "heading" in style:
                flush_paragraph()
                try:
                    heading_level = int(style.replace("heading", "").strip() or "1")
                except ValueError:
                    heading_level = 1
                blocks.append(
                    ContentBlock(
                        block_type=BlockType.HEADING,
                        text=text,
                        heading_level=heading_level,
                        metadata={"style_name": item.style.name if item.style else ""},
                    )
                )
            else:
                current_paragraph_lines.append(text)

        elif isinstance(item, Table):
            flush_paragraph()
            table_count += 1
            rows = []
            for row_idx, row in enumerate(item.rows):
                cells = [cell.text.strip() for cell in row.cells]
                row_str = " | ".join(cells)
                rows.append(row_str)
                if row_idx == 0:
                    # Add markdown table separator after header row
                    rows.append(" | ".join("---" for _ in cells))
            table_text = "\n".join(rows)
            if table_text.strip():
                lines.append(table_text)
                blocks.append(
                    ContentBlock(
                        block_type=BlockType.TABLE,
                        text=table_text,
                        metadata={"table_index": table_count - 1},
                    )
                )

    flush_paragraph()

    full_text = unicodedata.normalize("NFC", "\n".join(lines))
    return ParseResult(
        blocks=blocks,
        full_text=full_text,
        metadata={
            "file_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_name": filename,
        },
    )
