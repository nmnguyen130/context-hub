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
    assert result.blocks[0].heading_level == 1

    assert result.blocks[1].text == "Paragraph 1"
    assert result.blocks[1].block_type == BlockType.PARAGRAPH

    assert result.blocks[2].text == "print('hello')"
    assert result.blocks[2].block_type == BlockType.CODE
    assert result.blocks[2].language == "python"


def test_csv_parser():
    """Test parsing of CSV documents."""
    data = b"col1,col2\nval1,val2\nval3,val4"
    result = parse_csv(data, "test.csv")

    assert result.metadata["file_type"] == "text/csv"
    assert len(result.blocks) == 2
    assert "col1 | col2" in result.blocks[0].text
    assert "val1 | val2" in result.blocks[0].text
    assert result.blocks[0].block_type == BlockType.TABLE
    assert result.blocks[0].metadata["row_index"] == 1
    assert result.blocks[0].metadata["schema_hash"] is not None


def test_document_assembler():
    """Test text segmenting via the DocumentAssembler chunker engine."""
    assembler = DocumentAssembler(max_chunk_size=10, overlap_size=2)
    blocks = [
        ContentBlock(block_type=BlockType.PARAGRAPH, text="Hello world", page_number=1),
        ContentBlock(
            block_type=BlockType.PARAGRAPH, text="This is a test block", page_number=1
        ),
    ]
    chunks = assembler.chunk_document(
        full_text="Hello world\n\nThis is a test block", blocks=blocks
    )

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.content != ""
        assert chunk.token_count > 0
        assert 1 in chunk.metadata.page_numbers


def test_numbered_subsection_heading_classification():
    """Verify that subsections like '3.1 Encoder and Decoder Stacks' are correctly classified as level 2 headings."""
    assert classify_heading("3.1 Encoder and Decoder Stacks") == (
        2,
        "3.1 Encoder and Decoder Stacks",
    )
    assert classify_heading("3.1.2 Multi-Head Attention") == (
        3,
        "3.1.2 Multi-Head Attention",
    )
    assert classify_heading("1 Introduction") == (1, "1 Introduction")
    assert classify_heading("### 3.1 Encoder and Decoder Stacks") == (
        3,
        "3.1 Encoder and Decoder Stacks",
    )


def test_section_aware_chunk_boundaries():
    """Verify that subsections trigger a new chunk boundary instead of merging into previous chunk."""
    md_content = """# 3 Model Architecture

The Model Architecture section describes the overall design.

## 3.1 Encoder and Decoder Stacks

The encoder is composed of a stack of N = 6 identical layers.

## 3.2 Attention Mechanism

An attention function can be described as mapping a query and a set of key-value pairs."""

    blocks = scan_markdown_lines(md_content.splitlines(), page_number=1)
    chunks = select_chunks(md_content, blocks, section_break_level=2)

    assert len(chunks) == 3
    assert "3 Model Architecture" in chunks[0].metadata.heading_trail
    assert "3.1 Encoder and Decoder Stacks" in chunks[1].metadata.heading_trail
    assert "3.2 Attention Mechanism" in chunks[2].metadata.heading_trail
