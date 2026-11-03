"""Workspace CRUD, archive/restore, members, and templates."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.dependencies.dependencies import (
    get_workspace_member_service,
    get_workspace_service,
    get_workspace_template_service,
)
from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.domain.enums import WorkspaceRole, WorkspaceType
from collaboration_platform.workspace.member_service import WorkspaceMemberService
from collaboration_platform.workspace.template_service import WorkspaceTemplateService
from collaboration_platform.workspace.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    owner_id: str
    workspace_type: WorkspaceType = WorkspaceType.TEAM
    organization_id: str | None = None
    slug: str | None = None
    description: str | None = None
    template_id: str | None = None


@router.post("", status_code=201)
async def create_workspace(body: CreateWorkspaceRequest, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.create_workspace(
        name=body.name, owner_id=body.owner_id, workspace_type=body.workspace_type, organization_id=body.organization_id,
        slug=body.slug, description=body.description, template_id=body.template_id,
    ))


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.get(workspace_id))


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    settings: dict | None = None
    workspace_metadata: dict | None = None


@router.put("/{workspace_id}")
async def update_workspace(workspace_id: str, body: UpdateWorkspaceRequest, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.update(
        workspace_id, name=body.name, description=body.description, settings=body.settings, workspace_metadata=body.workspace_metadata,
    ))


@router.post("/{workspace_id}/archive")
async def archive_workspace(workspace_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.archive(workspace_id))


@router.post("/{workspace_id}/restore")
async def restore_workspace(workspace_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict(await service.restore(workspace_id))


@router.get("/owner/{owner_id}")
async def list_for_owner(owner_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict_list(await service.list_for_owner(owner_id))


@router.get("/organization/{organization_id}")
async def list_for_organization(organization_id: str, service: WorkspaceService = Depends(get_workspace_service)):
    return to_dict_list(await service.list_for_organization(organization_id))


class AddMemberRequest(BaseModel):
    user_id: str
    role: WorkspaceRole = WorkspaceRole.VIEWER
    invited_by: str | None = None


@router.post("/{workspace_id}/members", status_code=201)
async def add_member(workspace_id: str, body: AddMemberRequest, service: WorkspaceMemberService = Depends(get_workspace_member_service)):
    return to_dict(await service.add_member(workspace_id, body.user_id, role=body.role, invited_by=body.invited_by))


@router.get("/{workspace_id}/members")
async def list_members(workspace_id: str, service: WorkspaceMemberService = Depends(get_workspace_member_service)):
    return to_dict_list(await service.list_members(workspace_id))


class UpdateMemberRoleRequest(BaseModel):
    role: WorkspaceRole


@router.put("/{workspace_id}/members/{user_id}")
async def update_member_role(workspace_id: str, user_id: str, body: UpdateMemberRoleRequest, service: WorkspaceMemberService = Depends(get_workspace_member_service)):
    return to_dict(await service.update_role(workspace_id, user_id, role=body.role))


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(workspace_id: str, user_id: str, service: WorkspaceMemberService = Depends(get_workspace_member_service)):
    await service.remove_member(workspace_id, user_id)


@router.get("/templates/list")
async def list_templates(service: WorkspaceTemplateService = Depends(get_workspace_template_service)):
    return to_dict_list(await service.list_templates())


@router.post("/templates/seed-builtin")
async def seed_builtin_templates(service: WorkspaceTemplateService = Depends(get_workspace_template_service)):
    return {"created": await service.seed_builtin_templates()}
