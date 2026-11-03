"""Financial Analytics: infrastructure/model/token/storage/API cost,
cloud spend, cost per workspace/user/workflow, budget tracking, cost
forecasting inputs, ROI analysis — rolled up with `domain="financial"`.
`roi` is computed directly here (not through the engine) since return
on investment is a ratio of two already-rolled-up numbers, not a raw
event aggregation."""
from __future__ import annotations

from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.models.analytics import MetricRollupModel
from analytics_platform.repositories.registry import RepositoryRegistry

_DOMAIN = "financial"


class FinancialAnalyticsService:
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

    @staticmethod
    def compute_roi(*, value_generated: float, cost_incurred: float) -> float:
        """Standard ROI ratio: (gain - cost) / cost. Returns 0.0 if
        cost is zero rather than raising, since "no spend yet" is a
        legitimate state for a brand-new workspace, not an error."""
        if cost_incurred <= 0:
            return 0.0
        return (value_generated - cost_incurred) / cost_incurred
