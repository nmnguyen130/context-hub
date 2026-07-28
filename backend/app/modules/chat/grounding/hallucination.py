import re
from typing import Any

from app.modules.chat.text_utils import tokenize as _tokenize
from app.modules.documents.schemas import ScoredChunk


def check_faithfulness(
    response_text: str,
    chunks: list[ScoredChunk],
) -> tuple[float, list[dict[str, Any]]]:
    """Evaluate grounding faithfulness of response against source chunks using zero-cost token overlap.

    TODO (Level 2 SOTA Upgrade): For low-confidence queries or critical enterprise domains,
    escalate UNGROUNDED/PARTIAL claims to an NLI model (e.g. cross-encoder/nli-deberta) or
    a fast LLM-as-a-judge claim entailment check to eliminate API cost on simple queries.
    """
    if not response_text.strip() or not chunks:
        return 1.0, []

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", response_text)
        if s.strip() and not s.startswith("#")
    ]
    if not sentences:
        return 1.0, []

    chunk_word_sets = [_tokenize(chunk.content) for chunk in chunks]
    sentence_results = []
    grounded_score_sum = 0.0

    for sentence in sentences:
        sentence_words = _tokenize(sentence)
        if not sentence_words:
            grounded_score_sum += 1.0
            sentence_results.append(
                {"sentence": sentence, "status": "GROUNDED", "coverage": 1.0}
            )
            continue

        best_coverage = 0.0
        for chunk_words in chunk_word_sets:
            if not chunk_words:
                continue
            intersection = sentence_words & chunk_words
            coverage = len(intersection) / len(sentence_words)
            if coverage > best_coverage:
                best_coverage = coverage

        if best_coverage >= 0.50:
            status = "GROUNDED"
            grounded_score_sum += 1.0
        elif best_coverage >= 0.25:
            status = "PARTIAL"
            grounded_score_sum += 0.5
        else:
            status = "UNGROUNDED"

        sentence_results.append(
            {
                "sentence": sentence,
                "status": status,
                "coverage": round(best_coverage, 3),
            }
        )

    faithfulness_score = min(1.0, max(0.0, grounded_score_sum / len(sentences)))
    return round(faithfulness_score, 4), sentence_results
