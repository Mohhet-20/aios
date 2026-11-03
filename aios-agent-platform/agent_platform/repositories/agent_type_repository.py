from __future__ import annotations

from sqlalchemy import select

from agent_platform.models.agent_type import AgentTypeModel
from agent_platform.repositories.base import SQLAlchemyRepository


class AgentTypeRepository(SQLAlchemyRepository[AgentTypeModel]):
    model = AgentTypeModel

    async def get_by_key(self, key: str) -> AgentTypeModel | None:
        stmt = select(AgentTypeModel).where(AgentTypeModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_all(self) -> list[AgentTypeModel]:
        stmt = select(AgentTypeModel).order_by(AgentTypeModel.name)
        return list((await self.session.execute(stmt)).scalars().all())
