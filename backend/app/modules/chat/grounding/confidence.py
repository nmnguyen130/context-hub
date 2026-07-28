def compute_composite_confidence(
    retrieval_confidence: float,
    faithfulness_score: float,
    citation_coverage: float,
    cache_hit: bool = False,
) -> float:
    """Calculate composite confidence score combining retrieval, grounding, and citation signals."""
    if cache_hit:
        return 0.95

    score = (
        (retrieval_confidence * 0.35)
        + (faithfulness_score * 0.45)
        + (citation_coverage * 0.20)
    )
    return round(min(1.0, max(0.0, score)), 4)
