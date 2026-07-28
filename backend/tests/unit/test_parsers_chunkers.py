import pytest

from app.modules.documents.chunkers import DocumentAssembler, select_chunks
from app.modules.documents.parsers import (
    detect_mime_type,
    parse_csv,
    parse_markdown,
    parse_plaintext,
)
from app.modules.documents.parsers.markdown_scanner import (
    classify_heading,
    scan_markdown_lines,
)
from app.modules.documents.parsers.types import BlockType, ContentBlock
from app.modules.documents.security import apply_dlp, unmask_pii


def test_detect_mime_type():
    """Test automatic detection of MIME types from filename and content type."""
    assert detect_mime_type("test.pdf", None) == "application/pdf"
    assert (
        detect_mime_type("doc.docx", "application/octet-stream")
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert detect_mime_type("readme.md", None) == "text/markdown"
    assert detect_mime_type("data.csv", None) == "text/csv"
    assert detect_mime_type("unknown.xyz", "text/html") == "text/html"
    assert detect_mime_type("unknown.xyz", None) == "text/plain"


def test_plaintext_parser():
    """Test parsing of plaintext documents."""
    data = b"Line 1\nLine 2\n\nLine 3"
    result = parse_plaintext(data, "test.txt")

    assert result.metadata["file_type"] == "text/plain"
    assert result.metadata["document_name"] == "test.txt"
    assert len(result.blocks) == 2
    assert result.blocks[0].text == "Line 1 Line 2"
    assert result.blocks[0].block_type == BlockType.PARAGRAPH
    assert result.blocks[1].text == "Line 3"


def test_markdown_parser():
    """Test parsing of markdown documents."""
    data = b"# Header 1\nParagraph 1\n\n```python\nprint('hello')\n```"
    result = parse_markdown(data, "test.md")

    assert result.metadata["file_type"] == "text/markdown"
    assert len(result.blocks) == 3
    assert result.blocks[0].text == "Header 1"
    assert result.blocks[0].block_type == BlockType.HEADING
    assert result.blocks[1].text == "Paragraph 1"
    assert result.blocks[2].text == "print('hello')"


def test_csv_parser_and_row_batching():
    """Test CSV parsing and row batching (M5)."""
    header = "id,name,role\n"
    rows = "".join([f"{i},User_{i},Developer\n" for i in range(1, 51)])
    csv_bytes = (header + rows).encode("utf-8")

    result = parse_csv(csv_bytes, "users.csv", batch_size=20)

    assert len(result.blocks) == 3
    for b in result.blocks:
        assert b.block_type == BlockType.TABLE
        assert "id | name | role" in b.text

    assert result.blocks[0].metadata["row_range"] == [1, 20]
    assert result.blocks[1].metadata["row_range"] == [21, 40]
    assert result.blocks[2].metadata["row_range"] == [41, 50]


def test_document_assembler_and_offsets():
    """Test text segmenting and incremental character offset calculations via DocumentAssembler (M4)."""
    p1 = "Paragraph one text about architecture."
    p2 = "Paragraph two text about performance."
    full_text = f"{p1}\n\n{p2}"

    blocks = [
        ContentBlock(block_type=BlockType.PARAGRAPH, text=p1, page_number=1),
        ContentBlock(block_type=BlockType.PARAGRAPH, text=p2, page_number=1),
    ]

    assembler = DocumentAssembler(max_chunk_size=10, overlap_size=0)
    chunks = assembler.chunk_document(full_text=full_text, blocks=blocks)

    assert len(chunks) == 2
    assert chunks[0].content == p1
    assert chunks[0].metadata.char_start == 0
    assert chunks[0].metadata.char_end == len(p1)

    assert chunks[1].content == p2
    assert chunks[1].metadata.char_start == len(p1) + 2
    assert chunks[1].metadata.char_end == len(full_text)


def test_dlp_mask_and_unmask_roundtrip():
    """Test DLP PII masking and unmasking roundtrip."""
    raw_text = "Please contact support@company.com or call 123-45-6789 for help."
    masked_text, warnings, vault = apply_dlp(
        raw_text, workspace_dlp_rules={"action": "MASK"}
    )

    assert "support@company.com" not in masked_text
    assert "123-45-6789" not in masked_text
    assert len(vault) == 2

    restored_text = unmask_pii(masked_text, vault)
    assert restored_text == raw_text
