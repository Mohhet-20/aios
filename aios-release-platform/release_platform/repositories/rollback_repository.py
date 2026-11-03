from __future__ import annotations

from sqlalchemy import select

from release_platform.models.rollback import RollbackModel
from release_platform.repositories.base import SQLAlchemyRepository


class RollbackRepository(SQLAlchemyRepository[RollbackModel]):
    model = RollbackModel

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[RollbackModel]:
        stmt = select(RollbackModel).where(RollbackModel.tenant_id == tenant_id, RollbackModel.deployment_id == deployment_id)
        return list((await self.session.execute(stmt)).scalars().all())
