from __future__ import annotations

from sqlalchemy import select

from agent_platform.models.delegation import DelegationModel
from agent_platform.repositories.base import SQLAlchemyRepository


class DelegationRepository(SQLAlchemyRepository[DelegationModel]):
    model = DelegationModel

    async def list_for_task(self, task_id: str) -> list[DelegationModel]:
        stmt = select(DelegationModel).where(DelegationModel.task_id == task_id).order_by(DelegationModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_agent(self, agent_id: str) -> list[DelegationModel]:
        stmt = select(DelegationModel).where(DelegationModel.to_agent_id == agent_id).order_by(DelegationModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
