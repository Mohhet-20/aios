from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from observability_platform.models.capacity import CapacityForecastModel, CapacitySnapshotModel
from observability_platform.repositories.base import SQLAlchemyRepository


class CapacitySnapshotRepository(SQLAlchemyRepository[CapacitySnapshotModel]):
    model = CapacitySnapshotModel

    async def history(
        self,
        tenant_id: str,
        resource_type: str,
        *,
        component_id: str | None = None,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[CapacitySnapshotModel]:
        stmt = select(CapacitySnapshotModel).where(
            CapacitySnapshotModel.tenant_id == tenant_id, CapacitySnapshotModel.resource_type == resource_type
        )
        if component_id:
            stmt = stmt.where(CapacitySnapshotModel.component_id == component_id)
        if since:
            stmt = stmt.where(CapacitySnapshotModel.captured_at >= since)
        stmt = stmt.order_by(CapacitySnapshotModel.captured_at.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class CapacityForecastRepository(SQLAlchemyRepository[CapacityForecastModel]):
    model = CapacityForecastModel

    async def latest_for_resource(
        self, tenant_id: str, resource_type: str, *, component_id: str | None = None
    ) -> CapacityForecastModel | None:
        stmt = select(CapacityForecastModel).where(
            CapacityForecastModel.tenant_id == tenant_id, CapacityForecastModel.resource_type == resource_type
        )
        if component_id:
            stmt = stmt.where(CapacityForecastModel.component_id == component_id)
        stmt = stmt.order_by(CapacityForecastModel.generated_at.desc()).limit(1)
        return (await self.session.execute(stmt)).scalars().first()
