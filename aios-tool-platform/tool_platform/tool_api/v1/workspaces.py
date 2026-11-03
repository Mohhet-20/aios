"""Workspace CRUD — the top of the resource hierarchy. Deliberately thin
(no dedicated service): a workspace is just identity + organization
membership, nothing else in this platform needs to gate creating one
beyond RBAC (a real deployment would require an org-level manage
permission, enforced by whatever layer issues the caller's identity)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.dependencies.dependencies import get_repos
from tool_platform.models.workspace import WorkspaceModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.tool_api.serialization import to_dict, to_dict_list

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
