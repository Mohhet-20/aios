from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.chaos import ChaosExperimentModel
from quality_platform.repositories.base import SQLAlchemyRepository


class ChaosExperimentRepository(SQLAlchemyRepository[ChaosExperimentModel]):
    model = ChaosExperimentModel

    async def list_for_tenant(self, tenant_id: str, *, failure_type: str | None = None, limit: int = 100) -> list[ChaosExperimentModel]:
        stmt = select(ChaosExperimentModel).where(ChaosExperimentModel.tenant_id == tenant_id)
        if failure_type:
            stmt = stmt.where(ChaosExperimentModel.failure_type == failure_type)
        stmt = stmt.order_by(ChaosExperimentModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
