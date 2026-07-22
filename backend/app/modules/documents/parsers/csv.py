import csv
import hashlib
import io
import unicodedata

from app.modules.documents.parsers.base import BaseParser, ParsedBlock, ParseResult


class CSVParser(BaseParser):
    def parse(self, data: bytes, filename: str) -> ParseResult:
        """Parse CSV raw bytes into structured table blocks and plain text."""
        text = data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
        schema_hash = hashlib.sha256(",".join(fieldnames).encode()).hexdigest()[:16]

        blocks: list[ParsedBlock] = []
        lines: list[str] = []
        header = " | ".join(fieldnames)
        lines.append(header)

        for row_index, row in enumerate(reader, start=1):
            row_text = " | ".join(str(row.get(col, "")) for col in fieldnames)
            lines.append(row_text)
            blocks.append(
                ParsedBlock(
                    text=f"{header}\n{row_text}",
                    content_type="table",
                    metadata={
                        "column_names": fieldnames,
                        "row_index": row_index,
                        "schema_hash": schema_hash,
                    },
                )
            )

        full_text = unicodedata.normalize("NFC", "\n".join(lines))
        return ParseResult(
            blocks=blocks,
            full_text=full_text,
            metadata={"file_type": "text/csv", "document_name": filename},
        )
