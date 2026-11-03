from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from analytics_platform.models.warehouse import MetricDefinitionModel, MetricEventModel
from analytics_platform.repositories.base import SQLAlchemyRepository


class MetricDefinitionRepository(SQLAlchemyRepository[MetricDefinitionModel]):
    model = MetricDefinitionModel

    async def get_by_key(self, tenant_id: str, key: str) -> MetricDefinitionModel | None:
        stmt = select(MetricDefinitionModel).where(
            MetricDefinitionModel.tenant_id == tenant_id, MetricDefinitionModel.key == key,
            MetricDefinitionModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, data_source: str | None = None) -> list[MetricDefinitionModel]:
        stmt = select(MetricDefinitionModel).where(
            MetricDefinitionModel.tenant_id == tenant_id, MetricDefinitionModel.is_deleted.is_(False),
        )
        if data_source:
            stmt = stmt.where(MetricDefinitionModel.data_source == data_source)
        return list((await self.session.execute(stmt)).scalars().all())


class MetricEventRepository(SQLAlchemyRepository[MetricEventModel]):
    model = MetricEventModel

    async def list_for_metric(
        self, tenant_id: str, metric_key: str, *, since: datetime | None = None, limit: int = 1000,
    ) -> list[MetricEventModel]:
        stmt = select(MetricEventModel).where(
            MetricEventModel.tenant_id == tenant_id, MetricEventModel.metric_key == metric_key,
        )
        if since is not None:
            stmt = stmt.where(MetricEventModel.occurred_at >= since)
        stmt = stmt.order_by(MetricEventModel.occurred_at.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        from sqlalchemy import delete

        stmt = delete(MetricEventModel).where(
            MetricEventModel.tenant_id == tenant_id, MetricEventModel.occurred_at < cutoff,
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
