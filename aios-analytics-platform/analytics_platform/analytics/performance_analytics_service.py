"""Performance Analytics: system throughput, API latency, workflow
duration, response time, error rate, availability, scalability,
infrastructure utilization, deployment frequency, recovery time —
rolled up with `domain="performance"`."""
from __future__ import annotations

from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.models.analytics import MetricRollupModel
from analytics_platform.repositories.registry import RepositoryRegistry

_DOMAIN = "performance"


class PerformanceAnalyticsService:
    def __init__(self, repos: RepositoryRegistry, *, engine: AggregationEngine | None = None):
        self.repos = repos
        self.engine = engine or AggregationEngine(repos)

    async def compute_rollup(
        self, tenant_id: str, metric_key: str, *, period: str, period_start, period_end, aggregation_type: str = "p95",
    ) -> MetricRollupModel:
        return await self.engine.compute_rollup(
            tenant_id, metric_key, domain=_DOMAIN, period=period, period_start=period_start,
            period_end=period_end, aggregation_type=aggregation_type,
        )

    async def list_rollups(self, tenant_id: str, metric_key: str, *, period: str | None = None) -> list[MetricRollupModel]:
        return await self.engine.list_rollups(tenant_id, metric_key, domain=_DOMAIN, period=period)

    @staticmethod
    def compute_availability(*, uptime_seconds: float, total_seconds: float) -> float:
        if total_seconds <= 0:
            return 0.0
        return min(1.0, uptime_seconds / total_seconds)
