import re

from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult
from app.modules.documents.parsers.base import ParsedBlock


class CodeChunker(BaseChunker):
    CODE_FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

    def chunk(
        self, text: str, blocks: list[ParsedBlock] | None = None
    ) -> list[ChunkResult]:
        """Chunk code blocks from pre-parsed blocks, falling back to markdown code fences."""
        code_items: list[tuple[str, str | None, list[int], int, int]] = []

        if blocks:
            for b in blocks:
                if b.content_type == "code":
                    pages = [b.page_number] if b.page_number is not None else []
                    code_items.append((b.text, b.metadata.get("language"), pages, 0, 0))

        if not code_items and text:
            for match in self.CODE_FENCE_RE.finditer(text):
                lang = match.group(1) or None
                code = match.group(2).strip()
                if code:
                    code_items.append((code, lang, [], match.start(), match.end()))

        return [
            ChunkResult(
                content=content,
                chunk_index=idx,
                token_count=self.estimate_tokens(content),
                metadata=ChunkMetadata(
                    page_numbers=pages,
                    content_type="code",
                    language=lang,
                    chunker_used="code",
                    char_start=start,
                    char_end=end,
                ),
            )
            for idx, (content, lang, pages, start, end) in enumerate(code_items)
        ]
