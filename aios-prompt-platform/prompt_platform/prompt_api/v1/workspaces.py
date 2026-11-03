"""Workspace/project CRUD — the top of the resource hierarchy every
prompt, experiment, and deployment hangs off of."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_api.dependencies import get_repos
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    slug: str
    organization_id: str


class CreateProjectRequest(BaseModel):
    name: str
    slug: str


@router.post("", status_code=201)
async def create_workspace(body: CreateWorkspaceRequest, repos: RepositoryRegistry = Depends(get_repos)):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name=body.name, slug=body.slug, organization_id=body.organization_id))
    return to_dict(ws)


@router.get("")
async def list_workspaces(organization_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.workspaces.list_by_organization(organization_id))


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.workspaces.get_or_404(workspace_id))


@router.post("/{workspace_id}/projects", status_code=201)
async def create_project(workspace_id: str, body: CreateProjectRequest, repos: RepositoryRegistry = Depends(get_repos)):
    project = await repos.projects.add(PromptProjectModel(workspace_id=workspace_id, name=body.name, slug=body.slug))
    return to_dict(project)


@router.get("/{workspace_id}/projects")
async def list_projects(workspace_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.projects.list_by_workspace(workspace_id))
