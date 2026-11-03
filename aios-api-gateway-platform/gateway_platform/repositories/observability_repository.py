from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from gateway_platform.models.observability import (
    AnalyticsSnapshotModel,
    DependencyEdgeModel,
    GatewayMetricModel,
)
from gateway_platform.repositories.base import SQLAlchemyRepository


class GatewayMetricRepository(SQLAlchemyRepository[GatewayMetricModel]):
    model = GatewayMetricModel

    async def list_recent(
        self, tenant_id: str, *, metric_type: str | None = None, limit: int = 500
    ) -> list[GatewayMetricModel]:
        stmt = select(GatewayMetricModel).where(GatewayMetricModel.tenant_id == tenant_id)
        if metric_type:
            stmt = stmt.where(GatewayMetricModel.metric_type == metric_type)
        stmt = stmt.order_by(GatewayMetricModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        from sqlalchemy import delete

        stmt = delete(GatewayMetricModel).where(
            GatewayMetricModel.tenant_id == tenant_id, GatewayMetricModel.recorded_at < cutoff,
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class DependencyEdgeRepository(SQLAlchemyRepository[DependencyEdgeModel]):
    model = DependencyEdgeModel

    async def get_edge(self, tenant_id: str, from_service: str, to_service: str) -> DependencyEdgeModel | None:
        stmt = select(DependencyEdgeModel).where(
            DependencyEdgeModel.tenant_id == tenant_id, DependencyEdgeModel.from_service == from_service,
            DependencyEdgeModel.to_service == to_service,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[DependencyEdgeModel]:
        stmt = select(DependencyEdgeModel).where(DependencyEdgeModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())


class AnalyticsSnapshotRepository(SQLAlchemyRepository[AnalyticsSnapshotModel]):
    model = AnalyticsSnapshotModel

    async def list_by_type(self, tenant_id: str, snapshot_type: str, *, limit: int = 50) -> list[AnalyticsSnapshotModel]:
        stmt = select(AnalyticsSnapshotModel).where(
            AnalyticsSnapshotModel.tenant_id == tenant_id, AnalyticsSnapshotModel.snapshot_type == snapshot_type,
        ).order_by(AnalyticsSnapshotModel.period_start.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        from sqlalchemy import delete

        stmt = delete(AnalyticsSnapshotModel).where(
            AnalyticsSnapshotModel.tenant_id == tenant_id, AnalyticsSnapshotModel.period_end < cutoff,
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
