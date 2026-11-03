"""Agent Registry & Builder: create/read/update/delete, lifecycle
transitions, health, tool-permission grants, and search/listing — the
"Agent Dashboard / Registry / Builder / Profiles" frontend surfaces."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_agent_service
from agent_platform.agent_api.serialization import to_dict, to_dict_list
from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.core.pagination import PaginationParams
from agent_platform.domain.enums import AgentHealthStatus, ToolPermissionLevel

router = APIRouter(prefix="/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    workspace_id: str
    agent_type_id: str
    name: str
    owner_id: str
    role: str | None = None
    instructions: str | None = None
    goals: list[str] = []
    capabilities: list[str] = []
    skills: list[str] = []
    slug: str | None = None
    configuration: dict = {}
    resource_limits: dict = {}
    memory_access: dict = {}
    is_autonomous: bool = True
    description: str | None = None
    tags: list[str] = []


class UpdateAgentRequest(BaseModel):
    fields: dict


class HealthUpdateRequest(BaseModel):
    health_status: AgentHealthStatus


class ToolPermissionRequest(BaseModel):
    tool_name: str
    level: ToolPermissionLevel
    granted_by: str


@router.post("", status_code=201)
async def create_agent(body: CreateAgentRequest, svc: AgentService = Depends(get_agent_service)):
    agent = await svc.create_agent(
        body.workspace_id, body.agent_type_id, name=body.name, owner_id=body.owner_id, role=body.role,
        instructions=body.instructions, goals=body.goals, capabilities=body.capabilities, skills=body.skills,
        slug=body.slug, configuration=body.configuration, resource_limits=body.resource_limits,
        memory_access=body.memory_access, is_autonomous=body.is_autonomous, description=body.description, tags=body.tags,
    )
    return to_dict(agent)


@router.get("")
async def list_agents(
    workspace_id: str, status: str | None = None, agent_type_id: str | None = None,
    page: int = 1, page_size: int = 20, svc: AgentService = Depends(get_agent_service),
):
    result = await svc.list_agents(workspace_id, status=status, agent_type_id=agent_type_id, pagination=PaginationParams(page=page, page_size=page_size))
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size}


@router.get("/search")
async def search_agents(workspace_id: str, q: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict_list(await svc.search_agents(workspace_id, q))


@router.get("/{agent_id}")
async def get_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.get_agent(agent_id))


@router.patch("/{agent_id}")
async def update_agent(agent_id: str, body: UpdateAgentRequest, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.update_agent(agent_id, **body.fields))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    await svc.delete_agent(agent_id)


@router.post("/{agent_id}/activate")
async def activate_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.activate(agent_id))


@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.pause(agent_id))


@router.post("/{agent_id}/resume")
async def resume_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.resume(agent_id))


@router.post("/{agent_id}/deprecate")
async def deprecate_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.deprecate(agent_id))


@router.post("/{agent_id}/archive")
async def archive_agent(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.archive(agent_id))


@router.put("/{agent_id}/health")
async def update_health(agent_id: str, body: HealthUpdateRequest, svc: AgentService = Depends(get_agent_service)):
    return to_dict(await svc.update_health(agent_id, body.health_status))


@router.post("/{agent_id}/tool-permissions", status_code=201)
async def grant_tool_permission(agent_id: str, body: ToolPermissionRequest, svc: AgentService = Depends(get_agent_service)):
    grant = await svc.grant_tool_permission(agent_id, body.tool_name, body.level, granted_by=body.granted_by)
    return to_dict(grant)


@router.get("/{agent_id}/tool-permissions")
async def list_tool_permissions(agent_id: str, svc: AgentService = Depends(get_agent_service)):
    return to_dict_list(await svc.list_tool_permissions(agent_id))


@router.delete("/{agent_id}/tool-permissions/{tool_name}", status_code=204)
async def revoke_tool_permission(agent_id: str, tool_name: str, svc: AgentService = Depends(get_agent_service)):
    await svc.revoke_tool_permission(agent_id, tool_name)
