from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_agent_service
from app.schemas.agent import AgentCreate, AgentRead
from app.security.permissions import Permission
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    service: AgentService = Depends(get_agent_service),
    _principal=Depends(require_permission(Permission.AGENT_WRITE)),
):
    from app.models.agent import AgentModel

    agent = AgentModel(
        workspace_id=payload.workspace_id,
        name=payload.name,
        role=payload.role,
        description=payload.description,
        model_id=payload.model_id,
        allowed_tool_ids=",".join(payload.allowed_tool_ids),
    )
    return await service.create(agent)


@router.get("", response_model=list[AgentRead])
async def list_agents(
    workspace_id: str | None = Query(default=None), service: AgentService = Depends(get_agent_service)
):
    return await service.list(workspace_id=workspace_id) if workspace_id else await service.list()


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: str, service: AgentService = Depends(get_agent_service)):
    return await service.get(agent_id)


@router.post("/{agent_id}/tools/{tool_id}/check")
async def check_tool_permission(
    agent_id: str, tool_id: str, service: AgentService = Depends(get_agent_service)
):
    await service.assert_tool_permitted(agent_id, tool_id)
    return {"agent_id": agent_id, "tool_id": tool_id, "permitted": True}


@router.post("/{agent_id}/runs", response_model=AgentRead)
async def record_agent_run(
    agent_id: str, success: bool = True, service: AgentService = Depends(get_agent_service)
):
    return await service.record_run(agent_id, success)
