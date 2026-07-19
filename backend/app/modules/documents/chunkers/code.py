"""Code block chunker."""

from __future__ import annotations

import re

from app.modules.documents.chunkers.base import BaseChunker, ChunkMetadata, ChunkResult


class CodeChunker(BaseChunker):
    CODE_FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

    def chunk(self, text: str, blocks: list | None = None) -> list[ChunkResult]:
        matches = list(self.CODE_FENCE_RE.finditer(text))
        if not matches:
            return []

        results: list[ChunkResult] = []
        for idx, match in enumerate(matches):
            language = match.group(1) or None
            code = match.group(2).strip()
            results.append(
                ChunkResult(
                    content=code,
                    chunk_index=idx,
                    token_count=self.estimate_tokens(code),
                    metadata=ChunkMetadata(
                        content_type="code",
                        language=language,
                        chunker_used="code",
                        char_start=match.start(),
                        char_end=match.end(),
                    ),
                )
            )
        return results
