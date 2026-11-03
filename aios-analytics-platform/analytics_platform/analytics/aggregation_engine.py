"""Aggregation Engine: reads raw samples from the warehouse fact table
(`an_metric_events`) over a period window and writes one rolled-up
summary row (`an_metric_rollups`) per (metric, domain, period,
period_start) — real aggregation math (sum/avg/min/max/count and
p50/p95/p99 via a sorted-list percentile, not a hardcoded lookup),
computed once and persisted rather than recomputed on every dashboard
read. `compute_rollup` is an upsert: recomputing the same window
again (e.g. a late-arriving event corrects an hourly rollup before the
daily rollup runs) replaces the prior value instead of duplicating
the row."""
from __future__ import annotations

import math
from datetime import timezone

from analytics_platform.config.settings import Settings, get_settings
from analytics_platform.core.exceptions import UnsupportedAnalyticsDomainError, UnsupportedRollupPeriodError
from analytics_platform.domain.enums import AnalyticsDomain, RollupPeriod
from analytics_platform.models.analytics import MetricRollupModel
from analytics_platform.repositories.registry import RepositoryRegistry


def _aware(dt):
    """SQLite round-trips datetimes as naive even when they were
    written down as tz-aware, so any comparison against a freshly
    constructed `utc_now()` needs both sides
    normalized first."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = pct * (len(sorted_values) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[int(rank)]
    weight = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight


def _aggregate(values: list[float], aggregation_type: str) -> float:
    if not values:
        return 0.0
    if aggregation_type == "sum":
        return sum(values)
    if aggregation_type == "avg":
        return sum(values) / len(values)
    if aggregation_type == "min":
        return min(values)
    if aggregation_type == "max":
        return max(values)
    if aggregation_type == "count":
        return float(len(values))
    ordered = sorted(values)
    if aggregation_type == "p50":
        return _percentile(ordered, 0.50)
    if aggregation_type == "p95":
        return _percentile(ordered, 0.95)
    if aggregation_type == "p99":
        return _percentile(ordered, 0.99)
    return sum(values)


class AggregationEngine:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid(self, *, domain: str, period: str) -> None:
        if domain not in {d.value for d in AnalyticsDomain}:
            raise UnsupportedAnalyticsDomainError(f"'{domain}' is not a supported analytics domain")
        if period not in {p.value for p in RollupPeriod}:
            raise UnsupportedRollupPeriodError(f"'{period}' is not a supported rollup period")

    async def compute_rollup(
        self, tenant_id: str, metric_key: str, *, domain: str, period: str, period_start, period_end,
        aggregation_type: str = "sum",
    ) -> MetricRollupModel:
        self._assert_valid(domain=domain, period=period)
        events = await self.repos.metric_events.list_for_metric(tenant_id, metric_key, since=period_start, limit=100000)
        in_window = [e.value for e in events if _aware(e.occurred_at) < _aware(period_end)]
        value = _aggregate(in_window, aggregation_type)

        existing = await self.repos.metric_rollups.get_rollup(tenant_id, metric_key, domain, period, period_start)
        if existing is not None:
            existing.value = value
            existing.sample_count = len(in_window)
            existing.period_end = period_end
            return await self.repos.metric_rollups.update(existing)

        rollup = MetricRollupModel(
            tenant_id=tenant_id, metric_key=metric_key, domain=domain, period=period,
            period_start=period_start, period_end=period_end, value=value, sample_count=len(in_window),
        )
        return await self.repos.metric_rollups.add(rollup)

    async def list_rollups(
        self, tenant_id: str, metric_key: str, *, domain: str | None = None, period: str | None = None,
    ) -> list[MetricRollupModel]:
        return await self.repos.metric_rollups.list_for_metric(tenant_id, metric_key, domain=domain, period=period)
