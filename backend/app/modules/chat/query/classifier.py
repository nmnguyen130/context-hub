"""Deterministic query complexity classifier."""

from __future__ import annotations

from enum import StrEnum


class QueryComplexity(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


def classify_query(query: str, history: list[str] | None = None) -> QueryComplexity:
    tokens = query.lower().split()

    has_comparison = any(w in tokens for w in ("compare", "versus", "vs", "difference"))
    has_multi_hop = any(
        phrase in query.lower()
        for phrase in ("and then", "after that", "based on")
    )
    has_aggregation = any(
        w in tokens for w in ("summarize", "list", "overview", "analyze")
    )
    is_short = len(tokens) <= 5
    is_question = query.strip().endswith("?")
    has_context_dependency = any(w in tokens for w in ("it", "this", "that", "they", "them"))

    complexity_score = sum(
        [
            has_comparison * 2,
            has_multi_hop * 3,
            has_aggregation * 2,
            (not is_short) * 1,
            has_context_dependency * 1,
        ]
    )

    if complexity_score >= 4:
        return QueryComplexity.COMPLEX
    if complexity_score >= 2 or (is_question and not is_short):
        return QueryComplexity.MODERATE
    return QueryComplexity.SIMPLE
