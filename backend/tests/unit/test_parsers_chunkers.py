import pytest

from app.modules.documents.chunkers.sliding_window import SlidingWindowChunker
from app.modules.documents.parsers import detect_mime_type
from app.modules.documents.parsers.base import ParsedBlock
from app.modules.documents.parsers.csv import CSVParser
from app.modules.documents.parsers.markdown import MarkdownParser
from app.modules.documents.parsers.plaintext import PlaintextParser


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
    parser = PlaintextParser()
    data = b"Line 1\nLine 2\n\nLine 3"
    result = parser.parse(data, "test.txt")

    assert result.metadata["file_type"] == "text/plain"
    assert result.metadata["document_name"] == "test.txt"
    assert len(result.blocks) == 3
    assert result.blocks[0].text == "Line 1"
    assert result.blocks[0].content_type == "prose"
    assert result.blocks[2].text == "Line 3"


def test_markdown_parser():
    """Test parsing of markdown documents."""
    parser = MarkdownParser()
    data = b"# Header 1\nParagraph 1\n\n```python\nprint('hello')\n```"
    result = parser.parse(data, "test.md")

    assert result.metadata["file_type"] == "text/markdown"
    assert len(result.blocks) == 3

    assert result.blocks[0].text == "Header 1"
    assert result.blocks[0].content_type == "heading"
    assert result.blocks[0].heading_level == 1

    assert result.blocks[1].text == "Paragraph 1"
    assert result.blocks[1].content_type == "prose"

    assert result.blocks[2].text == "print('hello')"
    assert result.blocks[2].content_type == "code"
    assert result.blocks[2].metadata["language"] == "python"


def test_csv_parser():
    """Test parsing of CSV documents."""
    parser = CSVParser()
    data = b"col1,col2\nval1,val2\nval3,val4"
    result = parser.parse(data, "test.csv")

    assert result.metadata["file_type"] == "text/csv"
    assert len(result.blocks) == 2
    assert result.blocks[0].text == "col1 | col2\nval1 | val2"
    assert result.blocks[0].content_type == "table"
    assert result.blocks[0].metadata["row_index"] == 1
    assert result.blocks[0].metadata["schema_hash"] is not None


def test_sliding_window_chunker():
    """Test text segmenting via the sliding window chunker."""
    chunker = SlidingWindowChunker(chunk_size=10, overlap=2)
    blocks = [
        ParsedBlock(text="Hello world", content_type="prose", page_number=1),
        ParsedBlock(text="This is a test block", content_type="prose", page_number=1),
    ]
    chunks = chunker.chunk(text="Hello world\n\nThis is a test block", blocks=blocks)

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.content != ""
        assert chunk.token_count > 0
        assert 1 in chunk.metadata.page_numbers
        assert chunk.metadata.chunker_used == "sliding_window"
