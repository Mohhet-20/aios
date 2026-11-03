"""Aggregation math over a set of already-fetched metric points. Kept
as pure functions over `list[float]` (no DB access) so they're trivial
to unit test and reusable from both the query service and the
performance-analysis service."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class AggregationResult:
    count: int
    sum: float
    avg: float
    min: float
    max: float
    p50: float
    p95: float
    p99: float


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile — a simple, honest approximation (no
    linear interpolation between ranks). Good enough for operational
    dashboards; a statistics-grade percentile engine would interpolate
    and is unnecessary complexity for this platform's needs."""
    if not sorted_values:
        return 0.0
    k = max(0, min(len(sorted_values) - 1, math.ceil(pct / 100 * len(sorted_values)) - 1))
    return sorted_values[k]


def aggregate(values: list[float]) -> AggregationResult:
    if not values:
        return AggregationResult(count=0, sum=0.0, avg=0.0, min=0.0, max=0.0, p50=0.0, p95=0.0, p99=0.0)
    sorted_values = sorted(values)
    total = sum(values)
    return AggregationResult(
        count=len(values),
        sum=total,
        avg=total / len(values),
        min=sorted_values[0],
        max=sorted_values[-1],
        p50=_percentile(sorted_values, 50),
        p95=_percentile(sorted_values, 95),
        p99=_percentile(sorted_values, 99),
    )


def bucketize(timestamps_values: list[tuple], bucket_seconds: int) -> dict[int, list[float]]:
    """Groups (timestamp, value) pairs into fixed-width time buckets,
    keyed by bucket-start epoch seconds — the primitive
    `MetricQueryService.aggregate_range` uses to produce a time series
    of aggregates rather than one aggregate over the whole range."""
    buckets: dict[int, list[float]] = {}
    for ts, value in timestamps_values:
        epoch = int(ts.timestamp())
        bucket_key = epoch - (epoch % bucket_seconds)
        buckets.setdefault(bucket_key, []).append(value)
    return buckets
