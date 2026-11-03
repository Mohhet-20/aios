"""Pure query-popularity aggregation — no DB/service imports."""
from __future__ import annotations

from collections import Counter


def top_queries(queries: list[str], *, limit: int = 10) -> list[tuple[str, int]]:
    """Case-insensitive frequency count, most-frequent first; ties
    broken by first-seen order (Counter.most_common's own tie-break)."""
    counts = Counter(q.strip().lower() for q in queries if q.strip())
    return counts.most_common(limit)
