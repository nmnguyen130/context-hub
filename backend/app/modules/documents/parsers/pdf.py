import pymupdf
import pymupdf4llm

from app.modules.documents.parsers.markdown_scanner import scan_markdown_lines
from app.modules.documents.parsers.types import ContentBlock, ParseResult


def parse_pdf(data: bytes, filename: str) -> ParseResult:
    """Universal layout-aware PDF parser for academic papers, legal contracts, reports, and CVs."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    blocks: list[ContentBlock] = []
    full_text_parts: list[str] = []

    try:
        page_chunks = pymupdf4llm.to_markdown(
            doc,
            page_chunks=True,
            header=False,
            footer=False,
            ignore_images=True,
            force_text=True,
        )
        for page_idx, page in enumerate(page_chunks):
            page_number = page.get("metadata", {}).get("page", page_idx + 1)
            page_md = page.get("text", "")

            if page_md.strip():
                full_text_parts.append(page_md)

            blocks.extend(
                scan_markdown_lines(page_md.splitlines(), page_number=page_number)
            )
    finally:
        doc.close()

    return ParseResult(
        blocks=blocks,
        full_text="\n\n".join(full_text_parts),
        metadata={"file_type": "application/pdf", "document_name": filename},
    )
