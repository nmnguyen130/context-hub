import re
import unicodedata

# PII Scanners for Data Loss Prevention (DLP)
PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "api_key": re.compile(
        r"\b(?:api_key|apikey|secret|token|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{24,})['\"]?\b",
        re.IGNORECASE,
    ),
}


def dlp_filter_hook(content: str) -> str:
    """
    Scans content for PII (SSN, Emails, Credit Cards, API Keys)
    and masks them to prevent data leakage in vector indices.
    """
    masked_content = content
    for pii_type, pattern in PII_PATTERNS.items():
        masked_content = pattern.sub(f"[[MASKED_{pii_type.upper()}]]", masked_content)
    return masked_content


class MarkdownStructureChunker:
    """
    Structure-aware chunker designed for Markdown content.
    Aligns overlaps to clean word boundaries and chunks continuously across pages
    to prevent sentence fragmentation and tiny low-context chunks.
    """

    def __init__(self, target_chunk_size: int = 2000, chunk_overlap: int = 200):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, text: str, document_name: str) -> list[dict]:
        if not text:
            return []

        # 1. Normalize text to Unicode NFC to ensure consistent Vietnamese accent matching
        normalized_text = unicodedata.normalize("NFC", text)

        # 2. Record page boundaries (offsets of form feed '\f')
        page_boundaries = []
        last_idx = 0
        while True:
            idx = normalized_text.find("\f", last_idx)
            if idx == -1:
                break
            page_boundaries.append(idx)
            last_idx = idx + 1

        def get_page_number(offset: int) -> int:
            page_num = 1
            for boundary in page_boundaries:
                if offset > boundary:
                    page_num += 1
                else:
                    break
            return page_num

        # 3. Find all paragraphs and their exact offsets in the normalized text
        paragraphs = []
        for match in re.finditer(r"(?:[^\n\f]|\n(?!\n|\f))+", normalized_text):
            para_text = match.group().strip()
            if para_text:
                paragraphs.append(
                    {"text": para_text, "start": match.start(), "end": match.end()}
                )

        # 4. Group paragraphs into atomic heading-based sections
        sections = []
        current_section = {
            "heading": "Root",
            "level": 0,
            "paragraphs": [],
        }

        for para in paragraphs:
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", para["text"])
            if heading_match:
                if current_section["paragraphs"]:
                    sections.append(current_section)
                level = len(heading_match.group(1))
                heading_title = heading_match.group(2).strip()
                current_section = {
                    "heading": heading_title,
                    "level": level,
                    "paragraphs": [para],
                }
            else:
                current_section["paragraphs"].append(para)

        if current_section["paragraphs"]:
            sections.append(current_section)

        # 5. Split large sections into paragraph subgroups (each <= target_chunk_size)
        units = []
        for sec in sections:
            sec_paras = sec["paragraphs"]
            current_subgroup = []
            current_subgroup_len = 0

            for p in sec_paras:
                p_len = len(p["text"])
                if (
                    current_subgroup
                    and current_subgroup_len + p_len > self.target_chunk_size
                ):
                    units.append(
                        {
                            "heading": sec["heading"],
                            "paragraphs": current_subgroup,
                            "length": current_subgroup_len,
                        }
                    )
                    current_subgroup = [p]
                    current_subgroup_len = p_len
                else:
                    current_subgroup.append(p)
                    current_subgroup_len += p_len + 2  # +2 for double newline join

            if current_subgroup:
                units.append(
                    {
                        "heading": sec["heading"],
                        "paragraphs": current_subgroup,
                        "length": current_subgroup_len,
                    }
                )

        # 6. Pack sections/subgroups into final chunks using paragraph-aligned overlaps
        chunks = []
        chunk_idx = 0
        current_chunk_paras = []
        current_chunk_len = 0
        current_section_title = "Root"
        primary_start_offset = 0

        for unit in units:
            if (
                current_chunk_paras
                and current_chunk_len + unit["length"] > self.target_chunk_size
            ):
                # Save previous accumulated chunk
                chunk_content = "\n\n".join(p["text"] for p in current_chunk_paras)
                scrubbed_text = dlp_filter_hook(chunk_content)
                start_page = get_page_number(primary_start_offset)

                chunks.append(
                    {
                        "chunk_index": chunk_idx,
                        "content": scrubbed_text,
                        "metadata": {
                            "chunk_index": chunk_idx,
                            "document_name": document_name,
                            "section_title": current_section_title,
                            "page_number": start_page,
                            "char_offsets": [
                                current_chunk_paras[0]["start"],
                                current_chunk_paras[-1]["end"],
                            ],
                        },
                    }
                )
                chunk_idx += 1

                # Compute paragraph-aligned sliding window overlap
                overlap_paras = []
                overlap_len = 0
                for p in reversed(current_chunk_paras):
                    p_len = len(p["text"])
                    if overlap_len + p_len > self.chunk_overlap:
                        break
                    overlap_paras.insert(0, p)
                    overlap_len += p_len + 2

                current_chunk_paras = overlap_paras + unit["paragraphs"]
                current_chunk_len = overlap_len + unit["length"]
                current_section_title = unit["heading"]
                primary_start_offset = unit["paragraphs"][0]["start"]
            else:
                current_chunk_paras.extend(unit["paragraphs"])
                current_chunk_len += unit["length"]
                # Update first primary start offset of the chunk
                if len(current_chunk_paras) == len(unit["paragraphs"]):
                    current_section_title = unit["heading"]
                    primary_start_offset = unit["paragraphs"][0]["start"]

        # Add remaining accumulated chunk
        if current_chunk_paras:
            chunk_content = "\n\n".join(p["text"] for p in current_chunk_paras)
            scrubbed_text = dlp_filter_hook(chunk_content)
            start_page = get_page_number(primary_start_offset)
            chunks.append(
                {
                    "chunk_index": chunk_idx,
                    "content": scrubbed_text,
                    "metadata": {
                        "chunk_index": chunk_idx,
                        "document_name": document_name,
                        "section_title": current_section_title,
                        "page_number": start_page,
                        "char_offsets": [
                            current_chunk_paras[0]["start"],
                            current_chunk_paras[-1]["end"],
                        ],
                    },
                }
            )

        return chunks
