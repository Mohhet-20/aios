"""Project CRUD — the finest-grained scope in the org hierarchy."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_project_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.organizations.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    workspace_id: str
    name: str
    slug: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest, service: ProjectService = Depends(get_project_service)):
    project = await service.create_project(body.workspace_id, name=body.name, slug=body.slug, description=body.description)
    return to_dict(project)


@router.get("/{project_id}")
async def get_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    return to_dict(await service.repos.projects.get_or_404(project_id))


@router.post("/{project_id}/archive")
async def archive_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    return to_dict(await service.archive(project_id))


@router.get("")
async def list_projects(workspace_id: str, service: ProjectService = Depends(get_project_service)):
    return to_dict_list(await service.list_for_workspace(workspace_id))
