from __future__ import annotations

from sqlalchemy import select

from analytics_platform.models.analytics import MetricRollupModel
from analytics_platform.repositories.base import SQLAlchemyRepository


class MetricRollupRepository(SQLAlchemyRepository[MetricRollupModel]):
    model = MetricRollupModel

    async def get_rollup(
        self, tenant_id: str, metric_key: str, domain: str, period: str, period_start,
    ) -> MetricRollupModel | None:
        stmt = select(MetricRollupModel).where(
            MetricRollupModel.tenant_id == tenant_id, MetricRollupModel.metric_key == metric_key,
            MetricRollupModel.domain == domain, MetricRollupModel.period == period,
            MetricRollupModel.period_start == period_start,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_metric(
        self, tenant_id: str, metric_key: str, *, domain: str | None = None, period: str | None = None, limit: int = 500,
    ) -> list[MetricRollupModel]:
        stmt = select(MetricRollupModel).where(
            MetricRollupModel.tenant_id == tenant_id, MetricRollupModel.metric_key == metric_key,
        )
        if domain:
            stmt = stmt.where(MetricRollupModel.domain == domain)
        if period:
            stmt = stmt.where(MetricRollupModel.period == period)
        stmt = stmt.order_by(MetricRollupModel.period_start.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
