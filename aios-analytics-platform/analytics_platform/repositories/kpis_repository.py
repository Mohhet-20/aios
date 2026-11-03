from __future__ import annotations

from sqlalchemy import select

from analytics_platform.models.kpis import KpiDefinitionModel, KpiSnapshotModel
from analytics_platform.repositories.base import SQLAlchemyRepository


class KpiDefinitionRepository(SQLAlchemyRepository[KpiDefinitionModel]):
    model = KpiDefinitionModel

    async def list_for_tenant(self, tenant_id: str, *, scope: str | None = None) -> list[KpiDefinitionModel]:
        stmt = select(KpiDefinitionModel).where(
            KpiDefinitionModel.tenant_id == tenant_id, KpiDefinitionModel.is_deleted.is_(False),
        )
        if scope:
            stmt = stmt.where(KpiDefinitionModel.scope == scope)
        return list((await self.session.execute(stmt)).scalars().all())


class KpiSnapshotRepository(SQLAlchemyRepository[KpiSnapshotModel]):
    model = KpiSnapshotModel

    async def list_for_kpi(self, tenant_id: str, kpi_id: str, *, limit: int = 200) -> list[KpiSnapshotModel]:
        stmt = select(KpiSnapshotModel).where(
            KpiSnapshotModel.tenant_id == tenant_id, KpiSnapshotModel.kpi_id == kpi_id,
        ).order_by(KpiSnapshotModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
