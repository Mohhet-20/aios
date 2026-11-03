from __future__ import annotations

from sqlalchemy import select

from release_platform.models.analytics import DeploymentMetricModel, ReleaseAdoptionSnapshotModel
from release_platform.repositories.base import SQLAlchemyRepository


class DeploymentMetricRepository(SQLAlchemyRepository[DeploymentMetricModel]):
    model = DeploymentMetricModel

    async def list_for_tenant(self, tenant_id: str, *, metric_type: str | None = None, limit: int = 500) -> list[DeploymentMetricModel]:
        stmt = select(DeploymentMetricModel).where(DeploymentMetricModel.tenant_id == tenant_id)
        if metric_type:
            stmt = stmt.where(DeploymentMetricModel.metric_type == metric_type)
        stmt = stmt.order_by(DeploymentMetricModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class ReleaseAdoptionSnapshotRepository(SQLAlchemyRepository[ReleaseAdoptionSnapshotModel]):
    model = ReleaseAdoptionSnapshotModel

    async def list_for_version(self, tenant_id: str, version: str) -> list[ReleaseAdoptionSnapshotModel]:
        stmt = select(ReleaseAdoptionSnapshotModel).where(
            ReleaseAdoptionSnapshotModel.tenant_id == tenant_id, ReleaseAdoptionSnapshotModel.version == version,
        ).order_by(ReleaseAdoptionSnapshotModel.snapshot_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())
