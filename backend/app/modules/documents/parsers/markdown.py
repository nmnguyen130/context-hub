"""Markdown parser preserving heading structure and code blocks accurately."""

from __future__ import annotations

import re
import unicodedata

from app.modules.documents.parsers.base import BaseParser, ParsedBlock, ParseResult


class MarkdownParser(BaseParser):
    HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

    def parse(self, data: bytes, filename: str) -> ParseResult:
        text = data.decode("utf-8", errors="replace")
        text = unicodedata.normalize("NFC", text)

        blocks: list[ParsedBlock] = []
        in_code_block = False
        code_lines: list[str] = []
        code_lang = "plaintext"

        for line in text.splitlines():
            stripped = line.strip()
            
            # Code block detection and grouping
            if stripped.startswith("```"):
                if in_code_block:
                    # Closing fence: flush code block
                    code_text = "\n".join(code_lines)
                    blocks.append(
                        ParsedBlock(
                            text=code_text,
                            content_type="code",
                            metadata={"code_block": True, "language": code_lang},
                        )
                    )
                    code_lines = []
                    in_code_block = False
                else:
                    # Opening fence
                    in_code_block = True
                    lang = stripped[3:].strip()
                    code_lang = lang if lang else "plaintext"
                continue

            if in_code_block:
                code_lines.append(line)
                continue

            if not stripped:
                continue

            match = self.HEADING_RE.match(stripped)
            if match:
                level = len(match.group(1))
                blocks.append(
                    ParsedBlock(
                        text=match.group(2),
                        heading_level=level,
                        content_type="heading",
                    )
                )
            else:
                blocks.append(ParsedBlock(text=stripped, content_type="prose"))

        # Fallback if code block was not closed
        if in_code_block and code_lines:
            blocks.append(
                ParsedBlock(
                    text="\n".join(code_lines),
                    content_type="code",
                    metadata={"code_block": True, "language": code_lang},
                )
            )

        return ParseResult(
            blocks=blocks,
            full_text=text,
            metadata={"file_type": "text/markdown", "document_name": filename},
        )
