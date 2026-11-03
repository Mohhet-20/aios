from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from infra_platform.models.observability import ClusterHealthCheckModel, InfraMetricModel
from infra_platform.repositories.base import SQLAlchemyRepository


class InfraMetricRepository(SQLAlchemyRepository[InfraMetricModel]):
    model = InfraMetricModel

    async def list_recent(self, tenant_id: str, *, metric_name: str | None = None, limit: int = 200) -> list[InfraMetricModel]:
        stmt = select(InfraMetricModel).where(InfraMetricModel.tenant_id == tenant_id)
        if metric_name:
            stmt = stmt.where(InfraMetricModel.metric_name == metric_name)
        stmt = stmt.order_by(InfraMetricModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_for_metric(self, tenant_id: str, metric_name: str, *, resource_id: str | None = None) -> InfraMetricModel | None:
        stmt = select(InfraMetricModel).where(InfraMetricModel.tenant_id == tenant_id, InfraMetricModel.metric_name == metric_name)
        if resource_id:
            stmt = stmt.where(InfraMetricModel.resource_id == resource_id)
        stmt = stmt.order_by(InfraMetricModel.recorded_at.desc()).limit(1)
        return (await self.session.execute(stmt)).scalars().first()

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(InfraMetricModel).where(
            InfraMetricModel.tenant_id == tenant_id, InfraMetricModel.recorded_at < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class ClusterHealthCheckRepository(SQLAlchemyRepository[ClusterHealthCheckModel]):
    model = ClusterHealthCheckModel

    async def latest_for_cluster(self, tenant_id: str, cluster_id: str) -> ClusterHealthCheckModel | None:
        stmt = select(ClusterHealthCheckModel).where(
            ClusterHealthCheckModel.tenant_id == tenant_id, ClusterHealthCheckModel.cluster_id == cluster_id
        ).order_by(ClusterHealthCheckModel.checked_at.desc()).limit(1)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_cluster(self, tenant_id: str, cluster_id: str, *, limit: int = 200) -> list[ClusterHealthCheckModel]:
        stmt = select(ClusterHealthCheckModel).where(
            ClusterHealthCheckModel.tenant_id == tenant_id, ClusterHealthCheckModel.cluster_id == cluster_id
        ).order_by(ClusterHealthCheckModel.checked_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
