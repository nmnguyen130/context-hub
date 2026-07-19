"""PDF text extraction via PyMuPDF with page tracking."""

from __future__ import annotations

import unicodedata
import pymupdf
import pymupdf4llm

from app.modules.documents.parsers.base import BaseParser, ParsedBlock, ParseResult


class PDFParser(BaseParser):
    def parse(self, data: bytes, filename: str) -> ParseResult:
        doc = pymupdf.open(stream=data, filetype="pdf")
        
        blocks: list[ParsedBlock] = []
        full_text_parts: list[str] = []
        
        # Parse page-by-page to accurately track page numbers
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            # Retrieve markdown for the specific page
            page_md = pymupdf4llm.to_markdown(doc, pages=[page_idx])
            full_text_parts.append(page_md)
            
            normalized = unicodedata.normalize("NFC", page_md)
            normalized = "\n".join(line.rstrip() for line in normalized.splitlines())
            
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
                    
        doc.close()
        full_text = "\n\n".join(full_text_parts)
        
        return ParseResult(
            blocks=blocks,
            full_text=full_text,
            metadata={"file_type": "application/pdf", "document_name": filename},
        )
