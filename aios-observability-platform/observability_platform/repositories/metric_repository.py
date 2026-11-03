from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from observability_platform.models.metrics import MetricDefinitionModel, MetricPointModel
from observability_platform.repositories.base import SQLAlchemyRepository


class MetricDefinitionRepository(SQLAlchemyRepository[MetricDefinitionModel]):
    model = MetricDefinitionModel

    async def get_by_name(self, tenant_id: str, name: str) -> MetricDefinitionModel | None:
        stmt = select(MetricDefinitionModel).where(
            MetricDefinitionModel.tenant_id == tenant_id,
            MetricDefinitionModel.name == name,
            MetricDefinitionModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()


class MetricPointRepository(SQLAlchemyRepository[MetricPointModel]):
    model = MetricPointModel

    async def query_range(
        self,
        tenant_id: str,
        metric_name: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        component_id: str | None = None,
        limit: int = 5000,
    ) -> list[MetricPointModel]:
        stmt = select(MetricPointModel).where(
            MetricPointModel.tenant_id == tenant_id, MetricPointModel.metric_name == metric_name
        )
        if start_time:
            stmt = stmt.where(MetricPointModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(MetricPointModel.timestamp <= end_time)
        if component_id:
            stmt = stmt.where(MetricPointModel.component_id == component_id)
        stmt = stmt.order_by(MetricPointModel.timestamp.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest(self, tenant_id: str, metric_name: str, *, component_id: str | None = None) -> MetricPointModel | None:
        stmt = select(MetricPointModel).where(
            MetricPointModel.tenant_id == tenant_id, MetricPointModel.metric_name == metric_name
        )
        if component_id:
            stmt = stmt.where(MetricPointModel.component_id == component_id)
        stmt = stmt.order_by(MetricPointModel.timestamp.desc()).limit(1)
        return (await self.session.execute(stmt)).scalars().first()

    async def count_total(
        self, tenant_id: str, *, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(MetricPointModel).where(MetricPointModel.tenant_id == tenant_id)
        if start_time:
            stmt = stmt.where(MetricPointModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(MetricPointModel.timestamp <= end_time)
        return (await self.session.execute(stmt)).scalar_one()

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(MetricPointModel).where(
            MetricPointModel.tenant_id == tenant_id, MetricPointModel.timestamp < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
