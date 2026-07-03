from app.modules.documents.chunkers import MarkdownStructureChunker, dlp_filter_hook


def test_dlp_pii_masking():
    """Verify that sensitive PII data is successfully scrubbed via DLP hooks."""
    text = (
        "Hello, my SSN is 123-45-6789. "
        "Contact me at user@domain.com or use credit card 1234-5678-9012-3456. "
        "Also, here is my secret token: api_key=abcdef123456abcdef123456abcdef."
    )
    scrubbed = dlp_filter_hook(text)

    assert "123-45-6789" not in scrubbed
    assert "user@domain.com" not in scrubbed
    assert "1234-5678-9012-3456" not in scrubbed
    assert "abcdef123456abcdef123456abcdef" not in scrubbed

    assert "[[MASKED_SSN]]" in scrubbed
    assert "[[MASKED_EMAIL]]" in scrubbed
    assert "[[MASKED_CREDIT_CARD]]" in scrubbed
    assert "[[MASKED_API_KEY]]" in scrubbed


def test_markdown_structure_chunker_basic():
    """Verify standard markdown headings and pages are chunked with correct metadata."""
    doc_text = (
        "# Heading 1\n\n"
        "This is paragraph 1 on page 1.\n\n"
        "## Sub-Heading 1.1\n\n"
        "This is paragraph 2 on page 1.\n"
        "\f"
        "# Heading 2\n\n"
        "This is paragraph 3 on page 2."
    )

    chunker = MarkdownStructureChunker(target_chunk_size=100)
    chunks = chunker.chunk_document(doc_text, "test_doc.md")

    assert len(chunks) >= 2

    # Check page 1 chunks
    p1_chunks = [c for c in chunks if c["metadata"]["page_number"] == 1]
    assert len(p1_chunks) > 0
    assert p1_chunks[0]["metadata"]["document_name"] == "test_doc.md"
    assert (
        "Heading 1" in p1_chunks[0]["metadata"]["section_title"]
        or "Sub-Heading 1.1" in p1_chunks[0]["metadata"]["section_title"]
    )

    # Check page 2 chunks
    p2_chunks = [c for c in chunks if c["metadata"]["page_number"] == 2]
    assert len(p2_chunks) > 0
    assert p2_chunks[0]["metadata"]["section_title"] == "Heading 2"
    assert "paragraph 3" in p2_chunks[0]["content"]


def test_dlp_action_mask():
    chunker = MarkdownStructureChunker(dlp_action="MASK")
    doc_text = "My email is user@test.com"
    chunks = chunker.chunk_document(doc_text, "test.md")
    assert "[[MASKED_EMAIL]]" in chunks[0]["content"]


def test_dlp_action_none():
    chunker = MarkdownStructureChunker(dlp_action="NONE")
    doc_text = "My email is user@test.com"
    chunks = chunker.chunk_document(doc_text, "test.md")
    assert "user@test.com" in chunks[0]["content"]


def test_dlp_action_reject():
    chunker = MarkdownStructureChunker(dlp_action="REJECT")
    doc_text = "My email is user@test.com"
    import pytest

    with pytest.raises(ValueError, match="PII detected"):
        chunker.chunk_document(doc_text, "test.md")
