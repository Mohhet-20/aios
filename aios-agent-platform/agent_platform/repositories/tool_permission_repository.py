from __future__ import annotations

from sqlalchemy import select

from agent_platform.models.tool_permission import AgentToolPermissionModel
from agent_platform.repositories.base import SQLAlchemyRepository


class AgentToolPermissionRepository(SQLAlchemyRepository[AgentToolPermissionModel]):
    model = AgentToolPermissionModel

    async def list_for_agent(self, agent_id: str) -> list[AgentToolPermissionModel]:
        stmt = select(AgentToolPermissionModel).where(AgentToolPermissionModel.agent_id == agent_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_agent_tool(self, agent_id: str, tool_name: str) -> AgentToolPermissionModel | None:
        stmt = select(AgentToolPermissionModel).where(
            AgentToolPermissionModel.agent_id == agent_id, AgentToolPermissionModel.tool_name == tool_name
        )
        return (await self.session.execute(stmt)).scalars().first()
