"""Workspace CRUD — the top of the resource hierarchy and isolation
boundary. Deliberately thin: a workspace is identity + organization
membership; nothing else in this platform gates creating one beyond
RBAC, enforced by whatever layer issues the caller's identity."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.dependencies.dependencies import get_repos
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.models.workspace import WorkspaceModel
from eval_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    slug: str
    organization_id: str


@router.post("", status_code=201)
async def create_workspace(body: CreateWorkspaceRequest, repos: RepositoryRegistry = Depends(get_repos)):
    workspace = await repos.workspaces.add(WorkspaceModel(name=body.name, slug=body.slug, organization_id=body.organization_id))
    return to_dict(workspace)


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.workspaces.get_or_404(workspace_id))


@router.get("")
async def list_workspaces_for_organization(organization_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.workspaces.list_by_organization(organization_id))
