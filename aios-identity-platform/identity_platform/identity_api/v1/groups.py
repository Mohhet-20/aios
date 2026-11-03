"""Groups — lightweight org-scoped principals for bundling role
grants."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_group_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.organizations.group_service import GroupService

router = APIRouter(prefix="/groups", tags=["groups"])


class CreateGroupRequest(BaseModel):
    organization_id: str
    name: str
    description: str | None = None


@router.post("", status_code=201)
async def create_group(body: CreateGroupRequest, service: GroupService = Depends(get_group_service)):
    return to_dict(await service.create_group(body.organization_id, name=body.name, description=body.description))


@router.get("")
async def list_groups(organization_id: str, service: GroupService = Depends(get_group_service)):
    return to_dict_list(await service.list_for_organization(organization_id))


class GroupMemberRequest(BaseModel):
    user_id: str


@router.post("/{group_id}/members", status_code=201)
async def add_group_member(group_id: str, body: GroupMemberRequest, service: GroupService = Depends(get_group_service)):
    return to_dict(await service.add_member(group_id, body.user_id))


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_group_member(group_id: str, user_id: str, service: GroupService = Depends(get_group_service)):
    await service.remove_member(group_id, user_id)


@router.get("/{group_id}/members")
async def list_group_members(group_id: str, service: GroupService = Depends(get_group_service)):
    return to_dict_list(await service.list_members(group_id))
