"""Workspace CRUD within an organization."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_workspace_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.organizations.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    organization_id: str
    name: str
    slug: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def create_workspace(body: CreateWorkspaceRequest, service: WorkspaceService = Depends(get_workspace_service)):
    workspace = await service.create_workspace(body.organization_id, name=body.name, slug=body.slug, description=body.description)
    return to_dict(workspace)


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.repos.workspaces.get_or_404(workspace_id))


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    settings: dict | None = None


@router.put("/{workspace_id}")
async def update_workspace(workspace_id: str, body: UpdateWorkspaceRequest, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.update(workspace_id, name=body.name, description=body.description, settings=body.settings))


@router.post("/{workspace_id}/archive")
async def archive_workspace(workspace_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.archive(workspace_id))


@router.get("")
async def list_workspaces(organization_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict_list(await service.list_for_organization(organization_id))
