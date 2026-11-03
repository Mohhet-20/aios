"""Session lifecycle: create (post-login), refresh (rotate the refresh
token), revoke, and list active sessions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_session_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.sessions.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    user_id: str
    organization_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    device_fingerprint: str | None = None


@router.post("", status_code=201)
async def create_session(body: CreateSessionRequest, service: SessionService = Depends(get_session_service)):
    result = await service.create_session(
        body.user_id, organization_id=body.organization_id, ip_address=body.ip_address,
        user_agent=body.user_agent, device_fingerprint=body.device_fingerprint,
    )
    return {"session": to_dict(result.session), "access_token": result.access_token, "refresh_token": result.raw_refresh_token}


class RefreshSessionRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_session(body: RefreshSessionRequest, service: SessionService = Depends(get_session_service)):
    result = await service.refresh(body.refresh_token)
    return {"session": to_dict(result.session), "access_token": result.access_token, "refresh_token": result.raw_refresh_token}


class RevokeSessionRequest(BaseModel):
    reason: str = "user_logout"


@router.post("/{session_id}/revoke")
async def revoke_session(session_id: str, body: RevokeSessionRequest, service: SessionService = Depends(get_session_service)):
    return to_dict(await service.revoke_session(session_id, reason=body.reason))


@router.post("/users/{user_id}/revoke-all")
async def revoke_all_sessions(user_id: str, service: SessionService = Depends(get_session_service)):
    return {"revoked_count": await service.revoke_all_for_user(user_id)}


@router.get("/users/{user_id}")
async def list_active_sessions(user_id: str, service: SessionService = Depends(get_session_service)):
    return to_dict_list(await service.list_active_for_user(user_id))
