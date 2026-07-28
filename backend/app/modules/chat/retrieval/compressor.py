import re
from dataclasses import replace

from app.core.config import settings
from app.modules.chat.query.classifier import QueryComplexity
from app.modules.chat.text_utils import tokenize
from app.modules.documents.parsers.types import estimate_tokens
from app.modules.documents.schemas import ScoredChunk

DEFAULT_MAX_CONTEXT_TOKENS = 2500

MODEL_CONTEXT_LIMITS = {
    "gemini-2.0-flash": 1_048_576,
    "gemini-2.5-flash": 1_048_576,
    "gemini-1.5-flash": 1_048_576,
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
}

COMPLEXITY_BUDGET_MULTIPLIER = {
    QueryComplexity.SIMPLE: 0.60,
    QueryComplexity.MODERATE: 0.80,
    QueryComplexity.COMPLEX: 1.00,
}


def compute_token_budget(
    model: str | None = None,
    system_prompt_tokens: int = 500,
    history_tokens: int = 1000,
    safety_margin: int = 1000,
) -> int:
    """Calculate effective context token budget based on target LLM context window."""
    target_model = model or settings.RAG_CHAT_MODEL
    max_context = MODEL_CONTEXT_LIMITS.get(target_model, 128_000)
    budget = max_context - system_prompt_tokens - history_tokens - safety_margin
    return max(min(budget, DEFAULT_MAX_CONTEXT_TOKENS), 500)


def score_sentence(
    sentence: str,
    query_tokens: set[str],
    idx: int,
) -> float:
    """Score individual sentence using query overlap, position decay, and entity density."""
    st_tokens = tokenize(sentence)
    if not st_tokens:
        return 0.0

    # 1. Query overlap (Jaccard similarity)
    if query_tokens:
        intersection = query_tokens & st_tokens
        union = query_tokens | st_tokens
        jaccard = len(intersection) / max(len(union), 1)
    else:
        jaccard = 0.0

    # 2. Lead-sentence position decay (earlier sentences in chunk get higher priority)
    position_score = 1.0 / (1.0 + 0.1 * idx)

    # 3. Technical entity density (proper nouns / numbers, excluding initial word)
    words = sentence.split()
    body_words = words[1:] if len(words) > 1 else words
    entity_count = sum(
        1 for w in body_words if w and (w[0].isupper() or w[0].isdigit())
    )
    entity_density = entity_count / max(len(words), 1)

    return (0.50 * jaccard) + (0.30 * position_score) + (0.20 * entity_density)


def _jaccard_overlap(set_a: set[str], set_b: set[str]) -> float:
    """Calculate Jaccard token overlap between two token sets."""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def compress_context(
    query: str,
    chunks: list[ScoredChunk],
    max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    complexity: QueryComplexity | str | None = None,
) -> list[ScoredChunk]:
    """Production-grade query-aware context compressor.

    Pipeline phases:
    - Adaptive budget scaling based on query complexity.
    - Whole-chunk greedy packing with cross-chunk MMR redundancy checks.
    - Query-aware sentence extraction for the boundary overflow chunk.
    - Headroom backfill for remaining budget.
    """
    if not chunks:
        return []

    # Phase 1: Determine effective token budget
    multiplier = (
        COMPLEXITY_BUDGET_MULTIPLIER.get(complexity, 1.00) if complexity else 1.00
    )
    effective_budget = max(1, int(max_tokens * multiplier))

    compressed: list[ScoredChunk] = []
    current_tokens = 0
    query_tokens = tokenize(query)

    # Track sentence-level token sets to ensure consistent MMR redundancy checks
    packed_sentence_sets: list[set[str]] = []

    def is_sentence_redundant(st_tokens: set[str], threshold: float = 0.80) -> bool:
        """Check if a sentence overlaps >threshold with any previously packed sentence."""
        if not st_tokens:
            return False
        for packed_set in packed_sentence_sets:
            if _jaccard_overlap(st_tokens, packed_set) >= threshold:
                return True
        return False

    def split_sentences(text: str) -> list[str]:
        """Split text cleanly on sentence boundaries."""
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    # Phase 2: Whole-chunk greedy packing
    for chunk in chunks:
        chunk_tokens = estimate_tokens(chunk.content)
        chunk_sentences = split_sentences(chunk.content)
        chunk_sentence_sets = [tokenize(s) for s in chunk_sentences if s]

        # Case A: Whole chunk fits within current budget
        if current_tokens + chunk_tokens <= effective_budget:
            # Check redundancy against packed sentence history
            if not any(
                is_sentence_redundant(st_set, threshold=0.85)
                for st_set in chunk_sentence_sets
            ):
                compressed.append(chunk)
                current_tokens += chunk_tokens
                packed_sentence_sets.extend(chunk_sentence_sets)
            continue

        # Case B: Chunk overflows budget -> Apply sentence-level extraction
        remaining_budget = effective_budget - current_tokens
        if remaining_budget <= 15:
            break

        if not chunk_sentences:
            continue

        # Score sentences in overflow chunk
        scored_sentences = [
            (s, score_sentence(s, query_tokens, idx), estimate_tokens(s), tokenize(s))
            for idx, s in enumerate(chunk_sentences)
        ]
        scored_sentences.sort(key=lambda item: item[1], reverse=True)

        extracted_sentences: list[str] = []
        extracted_tokens = 0

        # Phase 3: Pack top-scoring non-redundant sentences into remaining headroom
        for sentence, score, st_token_count, st_token_set in scored_sentences:
            if extracted_tokens + st_token_count > remaining_budget:
                continue
            if is_sentence_redundant(st_token_set, threshold=0.80):
                continue

            extracted_sentences.append(sentence)
            extracted_tokens += st_token_count
            packed_sentence_sets.append(st_token_set)

        if extracted_sentences:
            new_content = " ".join(extracted_sentences)
            new_meta = dict(chunk.metadata or {})
            new_meta["is_compressed"] = True
            compressed.append(replace(chunk, content=new_content, metadata=new_meta))
            current_tokens += extracted_tokens

        # Phase 4: Stop if budget headroom is exhausted
        if effective_budget - current_tokens <= 15:
            break

    return compressed
