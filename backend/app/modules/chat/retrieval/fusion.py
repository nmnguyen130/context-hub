"""Reciprocal Rank Fusion for hybrid retrieval."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import replace

from app.core.config import settings
from app.modules.documents.schemas import ScoredChunk


def reciprocal_rank_fusion(
    result_sets: list[list[ScoredChunk]],
    k: int | None = None,
) -> list[ScoredChunk]:
    k = k or settings.RAG_RRF_K
    scores: dict[uuid.UUID, float] = defaultdict(float)
    chunk_map: dict[uuid.UUID, ScoredChunk] = {}

    for result_set in result_sets:
        for rank, chunk in enumerate(result_set, start=1):
            scores[chunk.id] += 1.0 / (k + rank)
            chunk_map[chunk.id] = chunk

    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    return [replace(chunk_map[cid], rrf_score=scores[cid]) for cid in sorted_ids]
