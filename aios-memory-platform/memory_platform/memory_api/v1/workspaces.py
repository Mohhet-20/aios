"""Workspace CRUD — the top of the resource hierarchy and isolation
boundary every memory, knowledge base, and document hangs off of."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from memory_platform.memory_api.dependencies import get_repos
from memory_platform.memory_api.serialization import to_dict, to_dict_list
from memory_platform.models.workspace import WorkspaceModel
from memory_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    slug: str
    organization_id: str


@router.post("", status_code=201)
async def create_workspace(body: CreateWorkspaceRequest, repos: RepositoryRegistry = Depends(get_repos)):
    ws = await repos.workspaces.add(WorkspaceModel(name=body.name, slug=body.slug, organization_id=body.organization_id))
    return to_dict(ws)


@router.get("")
async def list_workspaces(organization_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.workspaces.list_by_organization(organization_id))


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.workspaces.get_or_404(workspace_id))
