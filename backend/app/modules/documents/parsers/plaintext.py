"""Plain text and log file parser."""

from __future__ import annotations

import unicodedata

from app.modules.documents.parsers.base import BaseParser, ParsedBlock, ParseResult


class PlaintextParser(BaseParser):
    def parse(self, data: bytes, filename: str) -> ParseResult:
        text = data.decode("utf-8", errors="replace")
        text = unicodedata.normalize("NFC", text)
        text = "\n".join(line.rstrip() for line in text.splitlines())

        blocks = [
            ParsedBlock(text=line.strip(), content_type="prose")
            for line in text.splitlines()
            if line.strip()
        ]

        return ParseResult(
            blocks=blocks,
            full_text=text,
            metadata={"file_type": "text/plain", "document_name": filename},
        )
