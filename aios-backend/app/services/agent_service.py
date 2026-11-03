"""AgentService — flagship service demonstrating the domain layer in active
use: `is_permitted_tool` is domain logic (`app.domain.entities.agent.Agent`)
invoked before any tool call is allowed to proceed, independent of how the
Agent row happens to be persisted.
"""

from __future__ import annotations

from app.application.services.base_service import BaseCRUDService
from app.core.exceptions import AuthorizationError
from app.domain.entities.agent import Agent as AgentEntity
from app.domain.value_objects.enums import AgentStatus
from app.models.agent import AgentModel
from app.repositories.agent_repository import AgentRepository


def _to_domain(model: AgentModel) -> AgentEntity:
    return AgentEntity(
        id=model.id,
        workspace_id=model.workspace_id,
        name=model.name,
        role=model.role,
        description=model.description,
        model_id=model.model_id,
        allowed_tool_ids=[t for t in model.allowed_tool_ids.split(",") if t],
        status=AgentStatus(model.status),
        runs_today=model.runs_today,
        success_rate=model.success_rate,
    )


class AgentService(BaseCRUDService[AgentModel]):
    def __init__(self, repository: AgentRepository):
        super().__init__(repository)

    async def list_by_workspace(self, workspace_id: str) -> list[AgentModel]:
        return await self.repository.list_by_workspace(workspace_id)

    async def assert_tool_permitted(self, agent_id: str, tool_id: str) -> None:
        model = await self.repository.get_or_404(agent_id)
        agent = _to_domain(model)
        if not agent.is_permitted_tool(tool_id):
            raise AuthorizationError(
                f"Agent '{agent.name}' is not permitted to call tool '{tool_id}'",
                agent_id=agent_id,
                tool_id=tool_id,
            )

    async def record_run(self, agent_id: str, success: bool) -> AgentModel:
        model = await self.repository.get_or_404(agent_id)
        total_prior = model.runs_today
        successes_prior = round(model.success_rate / 100 * total_prior) if total_prior else 0
        model.runs_today = total_prior + 1
        successes = successes_prior + (1 if success else 0)
        model.success_rate = round((successes / model.runs_today) * 100, 2)
        model.status = AgentStatus.ACTIVE.value
        return await self.repository.update(model)
