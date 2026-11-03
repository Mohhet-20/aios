from __future__ import annotations

from sqlalchemy import select

from release_platform.models.rollout import RolloutModel
from release_platform.repositories.base import SQLAlchemyRepository


class RolloutRepository(SQLAlchemyRepository[RolloutModel]):
    model = RolloutModel

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[RolloutModel]:
        stmt = select(RolloutModel).where(RolloutModel.tenant_id == tenant_id, RolloutModel.deployment_id == deployment_id)
        return list((await self.session.execute(stmt)).scalars().all())
