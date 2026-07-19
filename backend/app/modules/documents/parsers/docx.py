"""DOCX parser using python-docx."""

from __future__ import annotations

import io
import unicodedata

from docx import Document as DocxDocument

from app.modules.documents.parsers.base import BaseParser, ParsedBlock, ParseResult


class DocxParser(BaseParser):
    def parse(self, data: bytes, filename: str) -> ParseResult:
        doc = DocxDocument(io.BytesIO(data))
        blocks: list[ParsedBlock] = []
        lines: list[str] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            lines.append(text)
            style = (para.style.name or "").lower()
            heading_level = None
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
                        metadata={"style_name": para.style.name},
                    )
                )
            else:
                blocks.append(ParsedBlock(text=text, content_type="prose"))

        for table_index, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(" | ".join(cells))
            table_text = "\n".join(rows)
            lines.append(table_text)
            blocks.append(
                ParsedBlock(
                    text=table_text,
                    content_type="table",
                    metadata={"table_index": table_index},
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
