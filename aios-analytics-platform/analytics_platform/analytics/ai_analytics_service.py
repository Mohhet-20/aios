"""AI Analytics: prompt success rate, agent/workflow performance,
model usage/quality, inference latency, token consumption, context
utilization, memory effectiveness, tool usage, evaluation scores,
hallucination trends — rolled up with `domain="ai"`."""
from __future__ import annotations

from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.models.analytics import MetricRollupModel
from analytics_platform.repositories.registry import RepositoryRegistry

_DOMAIN = "ai"


class AiAnalyticsService:
    def __init__(self, repos: RepositoryRegistry, *, engine: AggregationEngine | None = None):
        self.repos = repos
        self.engine = engine or AggregationEngine(repos)

    async def compute_rollup(
        self, tenant_id: str, metric_key: str, *, period: str, period_start, period_end, aggregation_type: str = "avg",
    ) -> MetricRollupModel:
        return await self.engine.compute_rollup(
            tenant_id, metric_key, domain=_DOMAIN, period=period, period_start=period_start,
            period_end=period_end, aggregation_type=aggregation_type,
        )

    async def list_rollups(self, tenant_id: str, metric_key: str, *, period: str | None = None) -> list[MetricRollupModel]:
        return await self.engine.list_rollups(tenant_id, metric_key, domain=_DOMAIN, period=period)
