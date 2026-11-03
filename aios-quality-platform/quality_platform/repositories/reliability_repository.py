from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.reliability import ReliabilityMetricSnapshotModel, SloDefinitionModel
from quality_platform.repositories.base import SQLAlchemyRepository


class SloDefinitionRepository(SQLAlchemyRepository[SloDefinitionModel]):
    model = SloDefinitionModel

    async def get_by_name(self, tenant_id: str, name: str) -> SloDefinitionModel | None:
        stmt = select(SloDefinitionModel).where(
            SloDefinitionModel.tenant_id == tenant_id, SloDefinitionModel.name == name, SloDefinitionModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, service_ref: str | None = None) -> list[SloDefinitionModel]:
        stmt = select(SloDefinitionModel).where(
            SloDefinitionModel.tenant_id == tenant_id, SloDefinitionModel.is_deleted.is_(False),
        )
        if service_ref:
            stmt = stmt.where(SloDefinitionModel.service_ref == service_ref)
        return list((await self.session.execute(stmt)).scalars().all())


class ReliabilityMetricSnapshotRepository(SQLAlchemyRepository[ReliabilityMetricSnapshotModel]):
    model = ReliabilityMetricSnapshotModel

    async def list_for_service(
        self, tenant_id: str, service_ref: str, *, metric_type: str | None = None, limit: int = 500,
    ) -> list[ReliabilityMetricSnapshotModel]:
        stmt = select(ReliabilityMetricSnapshotModel).where(
            ReliabilityMetricSnapshotModel.tenant_id == tenant_id, ReliabilityMetricSnapshotModel.service_ref == service_ref,
        )
        if metric_type:
            stmt = stmt.where(ReliabilityMetricSnapshotModel.metric_type == metric_type)
        stmt = stmt.order_by(ReliabilityMetricSnapshotModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
