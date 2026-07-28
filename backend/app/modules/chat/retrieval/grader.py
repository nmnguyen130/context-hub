from dataclasses import dataclass
from statistics import mean

from app.modules.documents.schemas import ScoredChunk


@dataclass(slots=True)
class GradingResult:
    accepted: list[ScoredChunk]
    rejected: list[ScoredChunk]
    avg_confidence: float
    is_low_confidence: bool


def grade_relevance(
    chunks: list[ScoredChunk],
    threshold: float = 0.05,
) -> GradingResult:
    """Grade retrieved chunks based on rerank_score or rrf_score.

    Filters out irrelevant chunks and identifies if overall retrieval confidence is too low.
    """
    if not chunks:
        return GradingResult(
            accepted=[],
            rejected=[],
            avg_confidence=0.0,
            is_low_confidence=True,
        )

    accepted: list[ScoredChunk] = []
    rejected: list[ScoredChunk] = []

    for chunk in chunks:
        score = chunk.rerank_score if chunk.rerank_score > 0 else chunk.rrf_score
        if score >= threshold:
            accepted.append(chunk)
        else:
            rejected.append(chunk)

    scores = [c.rerank_score if c.rerank_score > 0 else c.rrf_score for c in accepted]
    avg_conf = mean(scores) if scores else 0.0
    is_low = avg_conf < threshold or len(accepted) == 0

    return GradingResult(
        accepted=accepted,
        rejected=rejected,
        avg_confidence=avg_conf,
        is_low_confidence=is_low,
    )
