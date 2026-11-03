from __future__ import annotations

from sqlalchemy import func, or_, select

from agent_platform.models.agent import AgentModel
from agent_platform.repositories.base import SQLAlchemyRepository


class AgentRepository(SQLAlchemyRepository[AgentModel]):
    model = AgentModel

    async def get_by_slug(self, workspace_id: str, slug: str) -> AgentModel | None:
        stmt = select(AgentModel).where(
            AgentModel.workspace_id == workspace_id, AgentModel.slug == slug, AgentModel.is_deleted.is_(False)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_workspace(self, workspace_id: str) -> list[AgentModel]:
        return await self.list(filters={"workspace_id": workspace_id})

    async def list_by_type(self, agent_type_id: str) -> list[AgentModel]:
        return await self.list(filters={"agent_type_id": agent_type_id})

    async def list_by_status(self, workspace_id: str, status: str) -> list[AgentModel]:
        return await self.list(filters={"workspace_id": workspace_id, "status": status})

    async def search(self, workspace_id: str, query: str) -> list[AgentModel]:
        stmt = select(AgentModel).where(
            AgentModel.workspace_id == workspace_id, AgentModel.is_deleted.is_(False),
            or_(func.lower(AgentModel.name).like(f"%{query.lower()}%"), func.lower(AgentModel.role).like(f"%{query.lower()}%")),
        )
        return list((await self.session.execute(stmt)).scalars().all())
