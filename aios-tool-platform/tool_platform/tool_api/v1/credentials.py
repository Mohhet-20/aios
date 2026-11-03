"""Credential Vault: create/list/rotate/revoke + tool bindings. Note
what's deliberately absent — there is no endpoint that returns a
decrypted secret. `VaultService.get_secret` exists only for the
Execution Engine's internal use at dispatch time; exposing plaintext
credentials over HTTP, even behind auth, is a needless blast-radius
expansion this API surface refuses to offer."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.credentials.vault_service import VaultService
from tool_platform.dependencies.dependencies import get_vault_service
from tool_platform.tool_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CreateCredentialRequest(BaseModel):
    workspace_id: str
    name: str
    credential_type: str
    secret_material: dict
    owner_id: str
    scopes: list[str] = []
    expires_at: datetime | None = None
    credential_metadata: dict = {}


class RotateCredentialRequest(BaseModel):
    new_secret_material: dict
    new_expires_at: datetime | None = None


class BindCredentialRequest(BaseModel):
    tool_id: str
    workspace_id: str
    credential_id: str
    is_default: bool = True


@router.post("", status_code=201)
async def create_credential(body: CreateCredentialRequest, svc: VaultService = Depends(get_vault_service)):
    return to_dict(await svc.create_credential(
        body.workspace_id, name=body.name, credential_type=body.credential_type, secret_material=body.secret_material,
        owner_id=body.owner_id, scopes=body.scopes, expires_at=body.expires_at, credential_metadata=body.credential_metadata,
    ))


@router.get("")
async def list_for_workspace(workspace_id: str, svc: VaultService = Depends(get_vault_service)):
    return to_dict_list(await svc.list_for_workspace(workspace_id))


@router.post("/{credential_id}/rotate")
async def rotate_credential(credential_id: str, body: RotateCredentialRequest, svc: VaultService = Depends(get_vault_service)):
    return to_dict(await svc.rotate_credential(credential_id, new_secret_material=body.new_secret_material, new_expires_at=body.new_expires_at))


@router.post("/{credential_id}/revoke")
async def revoke_credential(credential_id: str, svc: VaultService = Depends(get_vault_service)):
    return to_dict(await svc.revoke_credential(credential_id))


@router.post("/bindings", status_code=201)
async def bind_to_tool(body: BindCredentialRequest, svc: VaultService = Depends(get_vault_service)):
    return to_dict(await svc.bind_to_tool(body.tool_id, body.workspace_id, body.credential_id, is_default=body.is_default))


@router.get("/bindings/{tool_id}/default")
async def get_default_credential_for_tool(tool_id: str, workspace_id: str, svc: VaultService = Depends(get_vault_service)):
    return to_dict(await svc.get_default_credential_for_tool(tool_id, workspace_id))
