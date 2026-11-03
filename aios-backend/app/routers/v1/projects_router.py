from fastapi import APIRouter, Depends, Query, status

from app.dependencies.service_dependencies import get_project_service
from app.schemas.workspace import ProjectCreate, ProjectRead
from app.services.workspace_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, service: ProjectService = Depends(get_project_service)):
    from app.models.workspace import ProjectModel

    project = ProjectModel(
        workspace_id=payload.workspace_id, name=payload.name, description=payload.description
    )
    return await service.create(project)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    workspace_id: str | None = Query(default=None), service: ProjectService = Depends(get_project_service)
):
    return await service.list(workspace_id=workspace_id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    return await service.get(project_id)


@router.patch("/{project_id}/progress", response_model=ProjectRead)
async def update_progress(
    project_id: str, progress: int, service: ProjectService = Depends(get_project_service)
):
    return await service.update_progress(project_id, progress)
