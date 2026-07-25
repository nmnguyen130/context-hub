from app.core.config import settings
from app.modules.documents.chunkers.types import Chunk, ChunkMetadata
from app.modules.documents.parsers.types import BlockType, ContentBlock, estimate_tokens


class DocumentAssembler:
    """Unified, state-of-the-art chunking engine for Enterprise RAG.

    Maintains section lineage, preserves table headers, handles code blocks,
    and injects contextual lineage into all produced chunks.
    """

    def __init__(
        self,
        max_chunk_size: int | None = None,
        overlap_size: int | None = None,
        section_break_level: int = 3,
    ) -> None:
        self.max_chunk_size = max_chunk_size or settings.RAG_CHUNK_SIZE
        self.overlap_size = overlap_size or settings.RAG_CHUNK_OVERLAP
        self.section_break_level = section_break_level

    def chunk_document(
        self,
        full_text: str,
        blocks: list[ContentBlock] | None = None,
    ) -> list[Chunk]:
        """Assemble document blocks or text into optimal, contextual chunks."""
        if not blocks and not full_text:
            return []

        # If no blocks provided, synthesize paragraph blocks from full_text
        if not blocks:
            raw_paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
            blocks = [
                ContentBlock(block_type=BlockType.PARAGRAPH, text=p)
                for p in raw_paragraphs
            ]

        results: list[Chunk] = []

        # Heading hierarchy tracker: maps level (1-6) -> heading_text
        active_headings: dict[int, str] = {}
        current_page = 1
        search_offset = 0

        # Buffer for accumulating current chunk contents
        buffered_blocks: list[ContentBlock] = []
        buffered_pages: set[int] = set()
        buffered_tokens = 0
        buffered_heading_trail: tuple[str, ...] = ()

        def current_trail() -> tuple[str, ...]:
            levels = sorted(active_headings.keys())
            return tuple(active_headings[lvl] for lvl in levels)

        def flush_buffer(is_section_break: bool = False) -> None:
            nonlocal \
                buffered_blocks, \
                buffered_pages, \
                buffered_tokens, \
                buffered_heading_trail, \
                search_offset
            if not buffered_blocks:
                return

            chunk_text, content_type, language, extra_meta = self._format_chunk_content(
                buffered_blocks
            )

            token_count = estimate_tokens(chunk_text)
            pages = tuple(sorted(buffered_pages)) if buffered_pages else (1,)

            # Calculate exact character offsets using running search offset
            first_block_text = buffered_blocks[0].text
            char_start = (
                full_text.find(first_block_text, search_offset) if full_text else 0
            )
            if char_start < 0:
                char_start = search_offset
            char_end = char_start + len(chunk_text)
            search_offset = char_end

            chunk = Chunk(
                content=chunk_text,
                chunk_index=len(results),
                token_count=token_count,
                metadata=ChunkMetadata(
                    page_numbers=pages,
                    heading_trail=buffered_heading_trail,
                    char_start=char_start,
                    char_end=char_end,
                    content_type=content_type,
                    language=language,
                    extra=extra_meta,
                ),
            )
            results.append(chunk)

            if is_section_break:
                # Do NOT bleed tail blocks of previous section into a new section heading
                buffered_blocks, buffered_pages, buffered_tokens = [], set(), 0
                buffered_heading_trail = ()
            else:
                # Compute overlap blocks for continuity within long sections
                buffered_blocks, buffered_pages, buffered_tokens = (
                    self._compute_block_overlap(buffered_blocks)
                )

        for block in blocks:
            if block.page_number is not None:
                current_page = block.page_number

            # Update heading hierarchy if HEADING block
            if block.block_type == BlockType.HEADING:
                level = block.heading_level or 1
                # Clear all headings at or deeper than this level
                deeper_levels = [lvl for lvl in active_headings if lvl >= level]
                for lvl in deeper_levels:
                    del active_headings[lvl]
                active_headings[level] = block.text

                # Headings at level <= section_break_level cause a structural flush
                if level <= self.section_break_level:
                    if buffered_blocks:
                        flush_buffer(is_section_break=True)
                    buffered_heading_trail = current_trail()
                    # Major section title is preserved in metadata.heading_trail lineage
                    continue

                # Minor headings (level > section_break_level): capture trail if buffer is currently empty
                if not buffered_blocks or not buffered_heading_trail:
                    buffered_heading_trail = current_trail()

                buffered_blocks.append(block)
                if block.page_number is not None:
                    buffered_pages.add(block.page_number)
                else:
                    buffered_pages.add(current_page)
                buffered_tokens += estimate_tokens(block.text)
                continue

            # Update trail snapshot if empty
            if not buffered_heading_trail:
                buffered_heading_trail = current_trail()

            # Handle isolated large blocks (huge tables, large code, huge paragraphs)
            block_tokens = estimate_tokens(block.text)
            if block_tokens > self.max_chunk_size:
                flush_buffer(is_section_break=True)
                sub_chunks = self._split_large_block(
                    block,
                    buffered_heading_trail,
                    current_page,
                )
                results.extend(sub_chunks)
                buffered_heading_trail = current_trail()
                continue

            # Flush if adding this block exceeds max chunk size
            if buffered_tokens + block_tokens > self.max_chunk_size and buffered_blocks:
                flush_buffer(is_section_break=False)

            buffered_blocks.append(block)
            if block.page_number is not None:
                buffered_pages.add(block.page_number)
            else:
                buffered_pages.add(current_page)
            buffered_tokens += block_tokens

        flush_buffer(is_section_break=True)

        # Re-index chunks sequentially
        final_results = []
        for idx, c in enumerate(results):
            final_results.append(
                Chunk(
                    content=c.content,
                    chunk_index=idx,
                    token_count=c.token_count,
                    metadata=c.metadata,
                )
            )
        return final_results

    def _format_chunk_content(
        self,
        blocks: list[ContentBlock],
    ) -> tuple[str, str, str | None, dict]:
        """Combine accumulated blocks into formatted chunk string and derive content_type."""
        types = {b.block_type for b in blocks}
        language = next((b.language for b in blocks if b.language), None)

        if len(types) == 1:
            raw_type = list(types)[0]
            content_type = (
                raw_type.value if hasattr(raw_type, "value") else str(raw_type)
            )
        else:
            content_type = "mixed"

        extra_meta = {}
        for b in blocks:
            if b.metadata:
                extra_meta.update(b.metadata)

        body = "\n\n".join(b.text for b in blocks)
        return body, content_type, language, extra_meta

    def _compute_block_overlap(
        self, blocks: list[ContentBlock]
    ) -> tuple[list[ContentBlock], set[int], int]:
        """Retain tail blocks fitting within configured token overlap limit."""
        retained: list[ContentBlock] = []
        retained_pages: set[int] = set()
        retained_tokens = 0

        for b in reversed(blocks):
            # Don't overlap code, tables, headings, or formulas
            if b.block_type in (
                BlockType.TABLE,
                BlockType.CODE,
                BlockType.HEADING,
                BlockType.FORMULA,
            ):
                break
            b_tokens = estimate_tokens(b.text)
            if retained_tokens + b_tokens > self.overlap_size:
                break
            retained.insert(0, b)
            if b.page_number is not None:
                retained_pages.add(b.page_number)
            retained_tokens += b_tokens

        return retained, retained_pages, retained_tokens

    def _split_large_block(
        self,
        block: ContentBlock,
        heading_trail: tuple[str, ...],
        page_number: int,
    ) -> list[Chunk]:
        """Split an oversized block (table, code, or long prose) into valid chunks."""
        sub_chunks: list[Chunk] = []

        if block.block_type == BlockType.TABLE:
            lines = block.text.splitlines()
            if len(lines) > 2 and lines[0].startswith("|"):
                header_lines = lines[:2]  # header + separator
                data_rows = lines[2:]
                header_str = "\n".join(header_lines)
                header_tokens = estimate_tokens(header_str)

                current_rows: list[str] = []
                current_tokens = header_tokens

                for row in data_rows:
                    row_tokens = estimate_tokens(row)
                    if (
                        current_tokens + row_tokens > self.max_chunk_size
                        and current_rows
                    ):
                        formatted = header_str + "\n" + "\n".join(current_rows)
                        sub_chunks.append(
                            Chunk(
                                content=formatted,
                                chunk_index=len(sub_chunks),
                                token_count=estimate_tokens(formatted),
                                metadata=ChunkMetadata(
                                    page_numbers=(page_number,),
                                    heading_trail=heading_trail,
                                    content_type="table",
                                    extra=block.metadata,
                                ),
                            )
                        )
                        current_rows, current_tokens = [], header_tokens

                    current_rows.append(row)
                    current_tokens += row_tokens

                if current_rows:
                    formatted = header_str + "\n" + "\n".join(current_rows)
                    sub_chunks.append(
                        Chunk(
                            content=formatted,
                            chunk_index=len(sub_chunks),
                            token_count=estimate_tokens(formatted),
                            metadata=ChunkMetadata(
                                page_numbers=(page_number,),
                                heading_trail=heading_trail,
                                content_type="table",
                                extra=block.metadata,
                            ),
                        )
                    )
                return sub_chunks

        # For prose or code blocks: split by sentences/lines
        raw_type = (
            block.block_type.value
            if hasattr(block.block_type, "value")
            else str(block.block_type)
        )
        lines = block.text.splitlines()
        current_lines: list[str] = []
        current_tokens = 0

        for line in lines:
            line_tokens = estimate_tokens(line)
            if current_tokens + line_tokens > self.max_chunk_size and current_lines:
                formatted = "\n".join(current_lines)
                sub_chunks.append(
                    Chunk(
                        content=formatted,
                        chunk_index=len(sub_chunks),
                        token_count=estimate_tokens(formatted),
                        metadata=ChunkMetadata(
                            page_numbers=(page_number,),
                            heading_trail=heading_trail,
                            content_type=raw_type,
                            language=block.language,
                            extra=block.metadata,
                        ),
                    )
                )
                current_lines, current_tokens = [], 0

            current_lines.append(line)
            current_tokens += line_tokens

        if current_lines:
            formatted = "\n".join(current_lines)
            sub_chunks.append(
                Chunk(
                    content=formatted,
                    chunk_index=len(sub_chunks),
                    token_count=estimate_tokens(formatted),
                    metadata=ChunkMetadata(
                        page_numbers=(page_number,),
                        heading_trail=heading_trail,
                        content_type=raw_type,
                        language=block.language,
                        extra=block.metadata,
                    ),
                )
            )

        return sub_chunks
