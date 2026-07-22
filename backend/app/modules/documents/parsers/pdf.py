import unicodedata

import pymupdf
import pymupdf4llm

from app.modules.documents.parsers.base import BaseParser, ParsedBlock, ParseResult


class PDFParser(BaseParser):
    def parse(self, data: bytes, filename: str) -> ParseResult:
        """Parse PDF raw bytes into structured markdown blocks and prose with page numbers."""
        doc = pymupdf.open(stream=data, filetype="pdf")

        blocks: list[ParsedBlock] = []
        full_text_parts: list[str] = []

        try:
            # Single-pass page chunk extraction for high efficiency
            page_chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)
            for page_idx, page in enumerate(page_chunks):
                page_number = page.get("metadata", {}).get("page", page_idx + 1)
                page_md = page.get("text", "")
                full_text_parts.append(page_md)

                normalized = unicodedata.normalize("NFC", page_md)
                for line in normalized.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue

                    if stripped.startswith("## "):
                        blocks.append(
                            ParsedBlock(
                                text=stripped[3:].strip(),
                                page_number=page_number,
                                heading_level=2,
                                content_type="heading",
                            )
                        )
                    elif stripped.startswith("# "):
                        blocks.append(
                            ParsedBlock(
                                text=stripped[2:].strip(),
                                page_number=page_number,
                                heading_level=1,
                                content_type="heading",
                            )
                        )
                    else:
                        blocks.append(
                            ParsedBlock(
                                text=stripped,
                                page_number=page_number,
                                content_type="prose",
                            )
                        )
        finally:
            doc.close()

        full_text = "\n\n".join(full_text_parts)

        return ParseResult(
            blocks=blocks,
            full_text=full_text,
            metadata={"file_type": "application/pdf", "document_name": filename},
        )
