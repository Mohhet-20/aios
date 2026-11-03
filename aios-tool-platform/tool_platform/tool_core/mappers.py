"""ORM <-> domain-aggregate bridge for Tool, mirroring every prior AIOS
platform's mappers.py pattern."""
from __future__ import annotations

from tool_platform.domain.entities import Tool
from tool_platform.domain.enums import ToolStatus
from tool_platform.models.tool import ToolModel


def tool_to_domain(model: ToolModel) -> Tool:
    return Tool(
        id=model.id, workspace_id=model.workspace_id, organization_id=model.organization_id, name=model.name,
        slug=model.slug, owner_id=model.owner_id, category=model.category, description=model.description,
        author=model.author, tags=list(model.tags or []), status=ToolStatus(model.status),
        current_version_id=model.current_version_id, tool_metadata=dict(model.tool_metadata or {}),
    )


def apply_tool_domain_to_model(entity: Tool, model: ToolModel) -> None:
    model.status = entity.status.value
    model.current_version_id = entity.current_version_id
    model.tags = entity.tags
    model.tool_metadata = entity.tool_metadata
