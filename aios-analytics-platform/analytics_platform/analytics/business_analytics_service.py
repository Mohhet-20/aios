"""Business Intelligence: active users, organizations, workspace
growth, feature adoption, retention, engagement, satisfaction, task
completion, time saved, automation rate, productivity gains — every
one of these is a named metric rolled up through the shared
`AggregationEngine` with `domain="business"`. This service is a thin,
domain-locked facade over the engine rather than a parallel
implementation, so "business domain" rollups can never be computed
with the wrong aggregation math."""
from __future__ import annotations

from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.models.analytics import MetricRollupModel
from analytics_platform.repositories.registry import RepositoryRegistry

_DOMAIN = "business"


class BusinessAnalyticsService:
    def __init__(self, repos: RepositoryRegistry, *, engine: AggregationEngine | None = None):
        self.repos = repos
        self.engine = engine or AggregationEngine(repos)

    async def compute_rollup(
        self, tenant_id: str, metric_key: str, *, period: str, period_start, period_end, aggregation_type: str = "sum",
    ) -> MetricRollupModel:
        return await self.engine.compute_rollup(
            tenant_id, metric_key, domain=_DOMAIN, period=period, period_start=period_start,
            period_end=period_end, aggregation_type=aggregation_type,
        )

    async def list_rollups(self, tenant_id: str, metric_key: str, *, period: str | None = None) -> list[MetricRollupModel]:
        return await self.engine.list_rollups(tenant_id, metric_key, domain=_DOMAIN, period=period)
