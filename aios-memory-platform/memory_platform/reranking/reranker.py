"""Re-ranking: recomputes a composite score for each candidate from
similarity, importance, and recency rather than trusting raw vector
similarity alone — a memory that's a decent semantic match but was
created seconds ago and is highly important can reasonably outrank one
that's a slightly closer match but old and low-importance. Operates on
the generic `RetrievalResult`, so it works for memory entries, knowledge
items, or document chunks alike.
"""
from __future__ import annotations

import math
from datetime import datetime

from memory_platform.core.time_utils import as_aware_utc
from memory_platform.retrieval.schemas import RetrievalResult
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _recency_score(result: RetrievalResult, *, as_of: datetime, half_life_days: float = 14.0) -> float:
    anchor = result.last_accessed_at or result.created_at
    if anchor is None:
        return 0.5  # neutral when we have no timestamp to judge from
    days_elapsed = max(0.0, (as_of - as_aware_utc(anchor)).total_seconds() / 86400.0)
    return math.exp(-math.log(2) * days_elapsed / half_life_days)


def rerank(
    results: list[RetrievalResult], *, similarity_weight: float = 0.5, importance_weight: float = 0.3, recency_weight: float = 0.2,
    half_life_days: float = 14.0, as_of: datetime | None = None,
) -> list[RetrievalResult]:
    if not results:
        return []
    as_of = as_of or _now()

    max_similarity = max((r.score for r in results), default=1.0) or 1.0
    rescored: list[tuple[float, RetrievalResult]] = []
    for r in results:
        normalized_similarity = r.score / max_similarity if max_similarity else 0.0
        recency = _recency_score(r, as_of=as_of, half_life_days=half_life_days)
        composite = (similarity_weight * normalized_similarity) + (importance_weight * r.importance_score) + (recency_weight * recency)
        rescored.append((composite, r))

    rescored.sort(key=lambda pair: pair[0], reverse=True)
    reranked = []
    for composite, r in rescored:
        r.metadata = {**r.metadata, "rerank_score": composite}
        reranked.append(r)
    return reranked


def top_k(results: list[RetrievalResult], k: int) -> list[RetrievalResult]:
    return results[:k]
