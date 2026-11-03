"""ToolService: identity/ownership/lifecycle CRUD for the top-level
`ToolModel` record. Editing the actual contract (schema/config/
capabilities/auth requirement) lives in `version_service.py` — this
service only ever touches identity fields and drives the `Tool` domain
entity's lifecycle transitions."""
from __future__ import annotations

from slugify import slugify

from tool_platform.core.exceptions import ValidationError
from tool_platform.core.pagination import Page, PaginationParams
from tool_platform.models.tool import ToolModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.tool_core.mappers import apply_tool_domain_to_model, tool_to_domain


class ToolService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_tool(
        self, workspace_id: str, *, name: str, owner_id: str, category: str, organization_id: str,
        slug: str | None = None, description: str | None = None, author: str | None = None,
        tags: list[str] | None = None, tool_metadata: dict | None = None,
    ) -> ToolModel:
        resolved_slug = slug or slugify(name)
        existing = await self.repos.tools.get_by_slug(workspace_id, resolved_slug)
        if existing is not None:
            raise ValidationError(f"a tool with slug '{resolved_slug}' already exists in this workspace")

        return await self.repos.tools.add(ToolModel(
            workspace_id=workspace_id, organization_id=organization_id, name=name, slug=resolved_slug,
            description=description, owner_id=owner_id, category=category, author=author, tags=tags or [],
            tool_metadata=tool_metadata or {},
        ))

    async def get_tool(self, tool_id: str) -> ToolModel:
        return await self.repos.tools.get_or_404(tool_id)

    async def list_tools(
        self, workspace_id: str, params: PaginationParams, *, status: str | None = None, category: str | None = None
    ) -> Page[ToolModel]:
        filters: dict = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category
        return await self.repos.tools.paginated_list(params, filters=filters)

    async def search_tools(self, workspace_id: str, query: str) -> list[ToolModel]:
        return await self.repos.tools.search(workspace_id, query)

    async def update_tool(self, tool_id: str, **fields) -> ToolModel:
        tool = await self.repos.tools.get_or_404(tool_id)
        allowed = {"name", "description", "author", "tags", "category", "tool_metadata"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValidationError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(tool, key, value)
        return await self.repos.tools.update(tool)

    async def delete_tool(self, tool_id: str) -> None:
        tool = await self.repos.tools.get_or_404(tool_id)
        await self.repos.tools.delete(tool)

    # -- lifecycle ------------------------------------------------------------

    async def publish(self, tool_id: str, version_id: str) -> ToolModel:
        model = await self.repos.tools.get_or_404(tool_id)
        entity = tool_to_domain(model)
        entity.publish(version_id)
        apply_tool_domain_to_model(entity, model)
        return await self.repos.tools.update(model)

    async def deprecate(self, tool_id: str) -> ToolModel:
        return await self._apply_transition(tool_id, "deprecate")

    async def disable(self, tool_id: str) -> ToolModel:
        return await self._apply_transition(tool_id, "disable")

    async def enable(self, tool_id: str) -> ToolModel:
        return await self._apply_transition(tool_id, "enable")

    async def _apply_transition(self, tool_id: str, transition: str) -> ToolModel:
        model = await self.repos.tools.get_or_404(tool_id)
        entity = tool_to_domain(model)
        getattr(entity, transition)()
        apply_tool_domain_to_model(entity, model)
        return await self.repos.tools.update(model)
