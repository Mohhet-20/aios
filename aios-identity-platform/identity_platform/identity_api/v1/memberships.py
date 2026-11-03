"""Membership add/remove/list across every scope in the org
hierarchy — organization, workspace, team, and project."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_membership_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.organizations.membership_service import MembershipService

router = APIRouter(prefix="/memberships", tags=["memberships"])


class AddMemberRequest(BaseModel):
    user_id: str
    invited_by: str | None = None


@router.post("/organizations/{organization_id}", status_code=201)
async def add_organization_member(organization_id: str, body: AddMemberRequest, service: MembershipService = Depends(get_membership_service)):
    return to_dict(await service.add_organization_member(organization_id, body.user_id, invited_by=body.invited_by))


@router.delete("/organizations/{organization_id}/users/{user_id}")
async def remove_organization_member(organization_id: str, user_id: str, service: MembershipService = Depends(get_membership_service)):
    return to_dict(await service.remove_organization_member(organization_id, user_id))


@router.get("/organizations/{organization_id}")
async def list_organization_members(organization_id: str, service: MembershipService = Depends(get_membership_service)):
    return to_dict_list(await service.list_organization_members(organization_id))


@router.post("/workspaces/{workspace_id}", status_code=201)
async def add_workspace_member(workspace_id: str, body: AddMemberRequest, service: MembershipService = Depends(get_membership_service)):
    return to_dict(await service.add_workspace_member(workspace_id, body.user_id))


@router.delete("/workspaces/{workspace_id}/users/{user_id}", status_code=204)
async def remove_workspace_member(workspace_id: str, user_id: str, service: MembershipService = Depends(get_membership_service)):
    await service.remove_workspace_member(workspace_id, user_id)


@router.get("/workspaces/{workspace_id}")
async def list_workspace_members(workspace_id: str, service: MembershipService = Depends(get_membership_service)):
    return to_dict_list(await service.list_workspace_members(workspace_id))


@router.post("/teams/{team_id}", status_code=201)
async def add_team_member(team_id: str, body: AddMemberRequest, service: MembershipService = Depends(get_membership_service)):
    return to_dict(await service.add_team_member(team_id, body.user_id))


@router.delete("/teams/{team_id}/users/{user_id}", status_code=204)
async def remove_team_member(team_id: str, user_id: str, service: MembershipService = Depends(get_membership_service)):
    await service.remove_team_member(team_id, user_id)


@router.get("/teams/{team_id}")
async def list_team_members(team_id: str, service: MembershipService = Depends(get_membership_service)):
    return to_dict_list(await service.list_team_members(team_id))


@router.post("/projects/{project_id}", status_code=201)
async def add_project_member(project_id: str, body: AddMemberRequest, service: MembershipService = Depends(get_membership_service)):
    return to_dict(await service.add_project_member(project_id, body.user_id))


@router.delete("/projects/{project_id}/users/{user_id}", status_code=204)
async def remove_project_member(project_id: str, user_id: str, service: MembershipService = Depends(get_membership_service)):
    await service.remove_project_member(project_id, user_id)


@router.get("/projects/{project_id}")
async def list_project_members(project_id: str, service: MembershipService = Depends(get_membership_service)):
    return to_dict_list(await service.list_project_members(project_id))
