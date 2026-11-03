from fastapi import APIRouter, Depends, Query, status

from app.dependencies.service_dependencies import get_workspace_service
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, service: WorkspaceService = Depends(get_workspace_service)
):
    from app.models.workspace import WorkspaceModel

    workspace = WorkspaceModel(
        organization_id=payload.organization_id, name=payload.name, color=payload.color
    )
    return await service.create(workspace)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    organization_id: str | None = Query(default=None),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await service.list(organization_id=organization_id)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(workspace_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return await service.get(workspace_id)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    await service.delete(workspace_id)
