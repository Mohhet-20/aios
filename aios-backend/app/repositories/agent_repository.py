from app.models.agent import AgentModel
from app.repositories.base import SQLAlchemyRepository


class AgentRepository(SQLAlchemyRepository[AgentModel]):
    model = AgentModel

    async def list_by_workspace(self, workspace_id: str) -> list[AgentModel]:
        return await self.list(workspace_id=workspace_id)
