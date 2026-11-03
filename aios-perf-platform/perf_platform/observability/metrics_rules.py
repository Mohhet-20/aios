"""Pure statistical helpers for the observability & benchmarking
module — zero DB/service imports. `percentile` is nearest-rank (nice
round numbers, no interpolation surprises); good enough for P50/P90/
P95/P99 dashboards and deterministic enough to unit-test exactly."""
from __future__ import annotations

import math


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if not 0 <= pct <= 100:
        raise ValueError(f"percentile must be in [0, 100], got {pct}")
    ordered = sorted(values)
    if pct == 0:
        return ordered[0]
    rank = math.ceil((pct / 100.0) * len(ordered))
    index = max(0, min(rank - 1, len(ordered) - 1))
    return ordered[index]


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def throughput_per_second(*, request_count: int, window_seconds: float) -> float:
    return round(request_count / window_seconds, 4) if window_seconds > 0 else 0.0


def improvement_pct(*, baseline_ms: float, optimized_ms: float) -> float:
    """Positive = faster (a real speedup); negative = a regression.
    Guards against divide-by-zero on a degenerate baseline."""
    if baseline_ms <= 0:
        return 0.0
    return round(100.0 * (baseline_ms - optimized_ms) / baseline_ms, 2)
