"""Tool CRUD + lifecycle (publish/deprecate/disable/enable) — the "Tool
Registry" / "Tool Builder" frontend surfaces."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.core.pagination import PaginationParams
from tool_platform.dependencies.dependencies import get_tool_service
from tool_platform.tool_api.serialization import to_dict, to_dict_list
from tool_platform.tool_core.tool_service import ToolService

router = APIRouter(prefix="/tools", tags=["tools"])


class CreateToolRequest(BaseModel):
    workspace_id: str
    name: str
    owner_id: str
    category: str
    organization_id: str
    slug: str | None = None
    description: str | None = None
    author: str | None = None
    tags: list[str] = []
    tool_metadata: dict = {}


class UpdateToolRequest(BaseModel):
    fields: dict


@router.post("", status_code=201)
async def create_tool(body: CreateToolRequest, svc: ToolService = Depends(get_tool_service)):
    tool = await svc.create_tool(
        body.workspace_id, name=body.name, owner_id=body.owner_id, category=body.category,
        organization_id=body.organization_id, slug=body.slug, description=body.description,
        author=body.author, tags=body.tags, tool_metadata=body.tool_metadata,
    )
    return to_dict(tool)


@router.get("")
async def list_tools(
    workspace_id: str, status: str | None = None, category: str | None = None,
    page: int = 1, page_size: int = 20, svc: ToolService = Depends(get_tool_service),
):
    result = await svc.list_tools(workspace_id, PaginationParams(page=page, page_size=page_size), status=status, category=category)
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size, "total_pages": result.total_pages}


@router.get("/search")
async def search_tools(workspace_id: str, q: str, svc: ToolService = Depends(get_tool_service)):
    return to_dict_list(await svc.search_tools(workspace_id, q))


@router.get("/{tool_id}")
async def get_tool(tool_id: str, svc: ToolService = Depends(get_tool_service)):
    return to_dict(await svc.get_tool(tool_id))


@router.patch("/{tool_id}")
async def update_tool(tool_id: str, body: UpdateToolRequest, svc: ToolService = Depends(get_tool_service)):
    return to_dict(await svc.update_tool(tool_id, **body.fields))


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(tool_id: str, svc: ToolService = Depends(get_tool_service)):
    await svc.delete_tool(tool_id)


@router.post("/{tool_id}/deprecate")
async def deprecate_tool(tool_id: str, svc: ToolService = Depends(get_tool_service)):
    return to_dict(await svc.deprecate(tool_id))


@router.post("/{tool_id}/disable")
async def disable_tool(tool_id: str, svc: ToolService = Depends(get_tool_service)):
    return to_dict(await svc.disable(tool_id))


@router.post("/{tool_id}/enable")
async def enable_tool(tool_id: str, svc: ToolService = Depends(get_tool_service)):
    return to_dict(await svc.enable(tool_id))
