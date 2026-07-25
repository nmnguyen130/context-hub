import re
import unicodedata

from app.modules.documents.parsers.types import BlockType, ContentBlock

MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+([A-Z0-9].*)$")
LEGAL_HEADING_RE = re.compile(
    r"^(?:SECTION|ARTICLE|CHAPTER|PART)\s+[0-9IVXLCDM]+[:\.\s-]*(.*)$",
    re.IGNORECASE,
)
LIST_ITEM_RE = re.compile(r"^(?:[\-\*\+]\s+|\d+[\.\)]\s+)")

# Matches mathematical equations or formulas
MATH_FORMULA_RE = re.compile(
    r"(?:\b[A-Z]{2,}\s*\([^\)]*\)\s*=|(?:\b(?:max|min|softmax|log|exp|arg\s*max)\s*\()|\s=\s|\\frac|\\sum|\\int)",
    re.IGNORECASE,
)


def classify_heading(line: str) -> tuple[int, str] | None:
    """Classify a single line as a heading.

    Returns (heading_level, clean_title_text) if line matches heading patterns, else None.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Filter out false-positive math formulas / equations misclassified as headings
    if MATH_FORMULA_RE.search(stripped):
        return None

    # Markdown heading # ...
    md_match = MARKDOWN_HEADING_RE.match(stripped)
    if md_match:
        level = len(md_match.group(1))
        return (level, md_match.group(2).strip())

    # Numbered heading (e.g. 1.2.3 Section Title or 3.1 Subsection Title)
    num_match = NUMBERED_HEADING_RE.match(stripped)
    if num_match:
        num_str = num_match.group(1).rstrip(".")
        dots_parts = num_str.split(".")
        level = min(max(len(dots_parts), 1), 6)
        return (level, stripped)

    # Legal clause heading (e.g. ARTICLE IV: Terms)
    if LEGAL_HEADING_RE.match(stripped):
        return (1, stripped)

    # ALL CAPS title (e.g. EXECUTIVE SUMMARY)
    if (
        2 < len(stripped) <= 60
        and stripped.isupper()
        and not stripped.endswith((".", ";", "?", "!"))
        and not any(c in stripped for c in (":", "@", "/", "\\"))
    ):
        return (2, stripped)

    return None


def scan_markdown_lines(
    lines: list[str], page_number: int | None = None
) -> list[ContentBlock]:
    """Process markdown-formatted lines into semantic blocks (paragraphs, headings, code, tables, lists, formulas)."""
    blocks: list[ContentBlock] = []

    in_code = False
    code_lines: list[str] = []
    code_lang = "plaintext"

    table_lines: list[str] = []
    list_lines: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(paragraph_lines).strip()
            if text:
                blocks.append(
                    ContentBlock(
                        block_type=BlockType.PARAGRAPH,
                        text=text,
                        page_number=page_number,
                    )
                )
            paragraph_lines = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            text = "\n".join(table_lines).strip()
            if text:
                blocks.append(
                    ContentBlock(
                        block_type=BlockType.TABLE,
                        text=text,
                        page_number=page_number,
                    )
                )
            table_lines = []

    def flush_list() -> None:
        nonlocal list_lines
        if list_lines:
            text = "\n".join(list_lines).strip()
            if text:
                blocks.append(
                    ContentBlock(
                        block_type=BlockType.LIST,
                        text=text,
                        page_number=page_number,
                    )
                )
            list_lines = []

    def flush_all() -> None:
        flush_paragraph()
        flush_table()
        flush_list()

    for line in lines:
        normalized_line = unicodedata.normalize("NFC", line)
        stripped = normalized_line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            flush_all()
            if in_code:
                blocks.append(
                    ContentBlock(
                        block_type=BlockType.CODE,
                        text="\n".join(code_lines),
                        page_number=page_number,
                        language=code_lang,
                        metadata={"code_block": True},
                    )
                )
                code_lines, in_code = [], False
            else:
                in_code = True
                lang = stripped[3:].strip()
                code_lang = lang or "plaintext"
            continue

        if in_code:
            code_lines.append(normalized_line)
            continue

        # Blank line breaks paragraphs, lists, tables
        if not stripped:
            flush_all()
            continue

        # Handle tables
        if stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 3:
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        else:
            flush_table()

        # Handle standalone formulas / equations
        if (
            stripped.startswith("### ")
            or stripped.startswith("$$")
            or stripped.startswith(r"\[")
        ) and MATH_FORMULA_RE.search(stripped):
            flush_all()
            clean_formula = stripped.lstrip("#$ ").rstrip("$ ").strip()
            blocks.append(
                ContentBlock(
                    block_type=BlockType.FORMULA,
                    text=clean_formula,
                    page_number=page_number,
                    metadata={"formula": True},
                )
            )
            continue

        # Check for heading
        heading_info = classify_heading(stripped)
        if heading_info:
            flush_all()
            level, heading_text = heading_info
            blocks.append(
                ContentBlock(
                    block_type=BlockType.HEADING,
                    text=heading_text,
                    heading_level=level,
                    page_number=page_number,
                )
            )
            continue

        # Handle list items
        if LIST_ITEM_RE.match(stripped):
            flush_paragraph()
            list_lines.append(stripped)
            continue
        elif list_lines and (
            normalized_line.startswith("  ") or normalized_line.startswith("\t")
        ):
            # Continuation of list item
            list_lines.append(stripped)
            continue
        else:
            flush_list()

        # Regular prose paragraph accumulation
        paragraph_lines.append(stripped)

    flush_all()
    if in_code and code_lines:
        blocks.append(
            ContentBlock(
                block_type=BlockType.CODE,
                text="\n".join(code_lines),
                page_number=page_number,
                language=code_lang,
                metadata={"code_block": True},
            )
        )

    return blocks
