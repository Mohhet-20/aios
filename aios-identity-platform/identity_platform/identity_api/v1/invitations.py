"""Email-addressed, token-based organization invitations."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_invitation_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.organizations.invitation_service import InvitationService

router = APIRouter(prefix="/invitations", tags=["invitations"])


class CreateInvitationRequest(BaseModel):
    organization_id: str
    email: str
    invited_by: str
    role_id: str | None = None
    workspace_id: str | None = None


@router.post("", status_code=201)
async def create_invitation(body: CreateInvitationRequest, service: InvitationService = Depends(get_invitation_service)):
    invitation, raw_token = await service.create_invitation(
        body.organization_id, email=body.email, invited_by=body.invited_by, role_id=body.role_id, workspace_id=body.workspace_id,
    )
    return {"invitation": to_dict(invitation), "token": raw_token}


class AcceptInvitationRequest(BaseModel):
    token: str
    user_id: str


@router.post("/accept")
async def accept_invitation(body: AcceptInvitationRequest, service: InvitationService = Depends(get_invitation_service)):
    user = await service.repos.users.get_or_404(body.user_id)
    return to_dict(await service.accept_invitation(body.token, user=user))


@router.post("/{invitation_id}/revoke")
async def revoke_invitation(invitation_id: str, service: InvitationService = Depends(get_invitation_service)):
    return to_dict(await service.revoke_invitation(invitation_id))


@router.get("/organizations/{organization_id}/pending")
async def list_pending_invitations(organization_id: str, service: InvitationService = Depends(get_invitation_service)):
    return to_dict_list(await service.list_pending_for_organization(organization_id))
