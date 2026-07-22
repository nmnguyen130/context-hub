import io
import unicodedata
from typing import Iterator

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.modules.documents.parsers.base import BaseParser, ParsedBlock, ParseResult


def _iter_block_items(doc: DocxDocument) -> Iterator[Paragraph | Table]:
    """Yield each paragraph and table child in sequential document body order."""
    body_elm = doc.element.body
    for child in body_elm.iterchildren():
        if child.tag.endswith("p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("tbl"):
            yield Table(child, doc)


class DocxParser(BaseParser):
    def parse(self, data: bytes, filename: str) -> ParseResult:
        """Parse DOCX raw bytes into structured headings, tables, and prose blocks in document order."""
        doc = DocxDocument(io.BytesIO(data))
        blocks: list[ParsedBlock] = []
        lines: list[str] = []
        table_count = 0

        for item in _iter_block_items(doc):
            if isinstance(item, Paragraph):
                text = item.text.strip()
                if not text:
                    continue
                lines.append(text)
                style = (item.style.name or "").lower() if item.style else ""
                if "heading" in style:
                    try:
                        heading_level = int(style.replace("heading", "").strip() or "1")
                    except ValueError:
                        heading_level = 1
                    blocks.append(
                        ParsedBlock(
                            text=text,
                            heading_level=heading_level,
                            content_type="heading",
                            metadata={
                                "style_name": item.style.name if item.style else ""
                            },
                        )
                    )
                else:
                    blocks.append(ParsedBlock(text=text, content_type="prose"))

            elif isinstance(item, Table):
                table_count += 1
                rows = []
                for row in item.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows.append(" | ".join(cells))
                table_text = "\n".join(rows)
                if table_text.strip():
                    lines.append(table_text)
                    blocks.append(
                        ParsedBlock(
                            text=table_text,
                            content_type="table",
                            metadata={"table_index": table_count - 1},
                        )
                    )

        full_text = unicodedata.normalize("NFC", "\n".join(lines))
        return ParseResult(
            blocks=blocks,
            full_text=full_text,
            metadata={
                "file_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "document_name": filename,
            },
        )
