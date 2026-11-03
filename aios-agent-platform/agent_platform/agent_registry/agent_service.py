"""Agent Registry + Agent Builder: creates agents from an AgentType's
defaults (with per-instance overrides), manages lifecycle transitions,
health status, tool-permission grants, and search/listing. This is the
service the "Agent Builder" and "Agent Profiles" frontend surfaces sit
on top of.
"""
from __future__ import annotations

from slugify import slugify

from agent_platform.core.exceptions import ValidationError
from agent_platform.core.pagination import Page, PaginationParams
from agent_platform.domain.enums import AgentHealthStatus, ToolPermissionLevel
from agent_platform.agent_registry.mappers import agent_to_domain, apply_agent_domain_to_model
from agent_platform.models.agent import AgentModel
from agent_platform.models.tool_permission import AgentToolPermissionModel
from agent_platform.repositories.registry import RepositoryRegistry


class AgentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- creation / builder ---------------------------------------------------

    async def create_agent(
        self, workspace_id: str, agent_type_id: str, *, name: str, owner_id: str,
        role: str | None = None, instructions: str | None = None, goals: list[str] | None = None,
        capabilities: list[str] | None = None, skills: list[str] | None = None, slug: str | None = None,
        configuration: dict | None = None, resource_limits: dict | None = None, memory_access: dict | None = None,
        is_autonomous: bool = True, description: str | None = None, tags: list[str] | None = None,
    ) -> AgentModel:
        agent_type = await self.repos.agent_types.get_or_404(agent_type_id)

        resolved_slug = slug or slugify(name)
        existing = await self.repos.agents.get_by_slug(workspace_id, resolved_slug)
        if existing is not None:
            raise ValidationError(f"an agent with slug '{resolved_slug}' already exists in this workspace")

        agent = await self.repos.agents.add(AgentModel(
            workspace_id=workspace_id, agent_type_id=agent_type_id, name=name, slug=resolved_slug, description=description,
            owner_id=owner_id, role=role or agent_type.name, instructions=instructions or agent_type.default_instructions,
            goals=goals or [], capabilities=capabilities or list(agent_type.default_capabilities),
            skills=skills or list(agent_type.default_skills), memory_access=memory_access or {}, configuration=configuration or {},
            resource_limits=resource_limits or dict(agent_type.default_resource_limits), is_autonomous=is_autonomous,
            tags=tags or [],
        ))

        for tool_name in agent_type.default_tool_names:
            await self.repos.tool_permissions.add(AgentToolPermissionModel(
                agent_id=agent.id, tool_name=tool_name, permission_level=ToolPermissionLevel.EXECUTE.value, granted_by=owner_id,
            ))

        return agent

    async def update_agent(self, agent_id: str, **fields) -> AgentModel:
        agent = await self.repos.agents.get_or_404(agent_id)
        for key, value in fields.items():
            setattr(agent, key, value)
        return await self.repos.agents.update(agent)

    async def delete_agent(self, agent_id: str) -> None:
        agent = await self.repos.agents.get_or_404(agent_id)
        await self.repos.agents.delete(agent)

    # -- lifecycle --------------------------------------------------------------

    async def _apply_transition(self, agent_id: str, transition: str) -> AgentModel:
        model = await self.repos.agents.get_or_404(agent_id)
        entity = agent_to_domain(model)
        getattr(entity, transition)()
        apply_agent_domain_to_model(entity, model)
        return await self.repos.agents.update(model)

    async def activate(self, agent_id: str) -> AgentModel:
        return await self._apply_transition(agent_id, "activate")

    async def pause(self, agent_id: str) -> AgentModel:
        return await self._apply_transition(agent_id, "pause")

    async def resume(self, agent_id: str) -> AgentModel:
        return await self._apply_transition(agent_id, "resume")

    async def deprecate(self, agent_id: str) -> AgentModel:
        return await self._apply_transition(agent_id, "deprecate")

    async def archive(self, agent_id: str) -> AgentModel:
        return await self._apply_transition(agent_id, "archive")

    async def update_health(self, agent_id: str, health: AgentHealthStatus) -> AgentModel:
        model = await self.repos.agents.get_or_404(agent_id)
        entity = agent_to_domain(model)
        entity.update_health(health)
        apply_agent_domain_to_model(entity, model)
        return await self.repos.agents.update(model)

    # -- tool permissions --------------------------------------------------------

    async def grant_tool_permission(self, agent_id: str, tool_name: str, level: ToolPermissionLevel, *, granted_by: str) -> AgentToolPermissionModel:
        await self.repos.agents.get_or_404(agent_id)
        existing = await self.repos.tool_permissions.get_for_agent_tool(agent_id, tool_name)
        if existing is not None:
            existing.permission_level = level.value
            existing.granted_by = granted_by
            return await self.repos.tool_permissions.update(existing)
        return await self.repos.tool_permissions.add(
            AgentToolPermissionModel(agent_id=agent_id, tool_name=tool_name, permission_level=level.value, granted_by=granted_by)
        )

    async def revoke_tool_permission(self, agent_id: str, tool_name: str) -> None:
        existing = await self.repos.tool_permissions.get_for_agent_tool(agent_id, tool_name)
        if existing is not None:
            await self.repos.tool_permissions.delete(existing, hard=True)

    async def list_tool_permissions(self, agent_id: str) -> list[AgentToolPermissionModel]:
        return await self.repos.tool_permissions.list_for_agent(agent_id)

    async def has_tool_permission(self, agent_id: str, tool_name: str, *, minimum: ToolPermissionLevel = ToolPermissionLevel.EXECUTE) -> bool:
        grant = await self.repos.tool_permissions.get_for_agent_tool(agent_id, tool_name)
        if grant is None:
            return False
        order = [ToolPermissionLevel.NONE, ToolPermissionLevel.READ_ONLY, ToolPermissionLevel.EXECUTE, ToolPermissionLevel.FULL]
        return order.index(ToolPermissionLevel(grant.permission_level)) >= order.index(minimum)

    # -- listing / search ---------------------------------------------------------

    async def get_agent(self, agent_id: str) -> AgentModel:
        return await self.repos.agents.get_or_404(agent_id)

    async def list_agents(self, workspace_id: str, *, status: str | None = None, agent_type_id: str | None = None, pagination: PaginationParams | None = None) -> Page[AgentModel]:
        pagination = pagination or PaginationParams()
        filters: dict = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        if agent_type_id:
            filters["agent_type_id"] = agent_type_id
        return await self.repos.agents.paginated_list(pagination, filters=filters)

    async def search_agents(self, workspace_id: str, query: str) -> list[AgentModel]:
        return await self.repos.agents.search(workspace_id, query)
