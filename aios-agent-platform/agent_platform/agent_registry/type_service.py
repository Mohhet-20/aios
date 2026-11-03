"""AgentTypeService: manages the data-driven agent-type registry —
built-in seeded types plus any custom types an enterprise customer
defines. Adding a new specialist to the platform is a call to
`create_type`, not a new Python class.
"""
from __future__ import annotations

from agent_platform.core.exceptions import NotFoundError, ValidationError
from agent_platform.domain.enums import AgentCategory
from agent_platform.models.agent_type import AgentTypeModel
from agent_platform.repositories.registry import RepositoryRegistry
from agent_platform.agent_registry.seed_types import seed_builtin_agent_types


class AgentTypeService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def seed_builtin_types(self) -> list[AgentTypeModel]:
        return await seed_builtin_agent_types(self.repos)

    async def create_type(
        self, *, key: str, name: str, default_instructions: str, category: AgentCategory = AgentCategory.CUSTOM,
        description: str | None = None, default_capabilities: list[str] | None = None, default_skills: list[str] | None = None,
        default_tool_names: list[str] | None = None, default_resource_limits: dict | None = None,
    ) -> AgentTypeModel:
        existing = await self.repos.agent_types.get_by_key(key)
        if existing is not None:
            raise ValidationError(f"agent type with key '{key}' already exists")
        return await self.repos.agent_types.add(AgentTypeModel(
            key=key, name=name, category=category.value, description=description, default_instructions=default_instructions,
            default_capabilities=default_capabilities or [], default_skills=default_skills or [],
            default_tool_names=default_tool_names or [], default_resource_limits=default_resource_limits or {}, is_builtin=False,
        ))

    async def get_type(self, agent_type_id: str) -> AgentTypeModel:
        return await self.repos.agent_types.get_or_404(agent_type_id)

    async def get_by_key(self, key: str) -> AgentTypeModel:
        model = await self.repos.agent_types.get_by_key(key)
        if model is None:
            raise NotFoundError(f"agent type '{key}' not found")
        return model

    async def list_types(self) -> list[AgentTypeModel]:
        return await self.repos.agent_types.list_all()
