"""Credential Vault API: secret CRUD, rotation, lifecycle transitions,
access-policy-gated reads, access grants, and environment injection."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import (
    get_current_actor_id,
    get_current_tenant_id,
    get_secret_access_service,
    get_secret_service,
)
from security_platform.secrets.access_service import SecretAccessService
from security_platform.secrets.secret_service import SecretService
from security_platform.sec_api.serialization import to_dict

router = APIRouter(prefix="/secrets", tags=["secrets"])


class CreateSecretRequest(BaseModel):
    name: str
    secret_type: str
    plaintext_value: str
    owner_id: str | None = None
    description: str | None = None
    expires_at: datetime | None = None


@router.post("", status_code=201)
async def create_secret(
    body: CreateSecretRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: SecretService = Depends(get_secret_service),
):
    secret = await service.create_secret(tenant_id, **body.model_dump(), created_by=actor_id)
    return to_dict(secret)


class RotateSecretRequest(BaseModel):
    new_plaintext_value: str


@router.post("/{secret_id}/rotate")
async def rotate_secret(
    secret_id: str, body: RotateSecretRequest, tenant_id: str = Depends(get_current_tenant_id),
    actor_id: str | None = Depends(get_current_actor_id), service: SecretService = Depends(get_secret_service),
):
    return to_dict(await service.rotate_secret(tenant_id, secret_id, body.new_plaintext_value, rotated_by=actor_id))


@router.post("/{secret_id}/revoke")
async def revoke_secret(secret_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecretService = Depends(get_secret_service)):
    return to_dict(await service.revoke_secret(tenant_id, secret_id))


@router.post("/{secret_id}/expire")
async def expire_secret(secret_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecretService = Depends(get_secret_service)):
    return to_dict(await service.expire_secret(tenant_id, secret_id))


class RenewSecretRequest(BaseModel):
    extend_expires_at: datetime | None = None


@router.post("/{secret_id}/renew")
async def renew_secret(
    secret_id: str, body: RenewSecretRequest, tenant_id: str = Depends(get_current_tenant_id), service: SecretService = Depends(get_secret_service)
):
    return to_dict(await service.renew_secret(tenant_id, secret_id, extend_expires_at=body.extend_expires_at))


@router.get("/{secret_id}/value")
async def get_secret_value(
    secret_id: str, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: SecretService = Depends(get_secret_service),
):
    return {"value": await service.get_secret_value(tenant_id, secret_id, actor_id or "unknown")}


class InjectEnvironmentRequest(BaseModel):
    secret_names: list[str]


@router.post("/inject-environment")
async def inject_for_environment(
    body: InjectEnvironmentRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: SecretService = Depends(get_secret_service),
):
    return await service.inject_for_environment(tenant_id, body.secret_names, actor_id or "unknown")


class GrantAccessRequest(BaseModel):
    principal_id: str
    can_read: bool = True
    can_rotate: bool = False
    expires_at: datetime | None = None


@router.post("/{secret_id}/access", status_code=201)
async def grant_access(
    secret_id: str, body: GrantAccessRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: SecretAccessService = Depends(get_secret_access_service),
):
    return to_dict(
        await service.grant_access(tenant_id, secret_id, body.principal_id, can_read=body.can_read, can_rotate=body.can_rotate, expires_at=body.expires_at)
    )


@router.delete("/{secret_id}/access/{principal_id}", status_code=204)
async def revoke_access(
    secret_id: str, principal_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SecretAccessService = Depends(get_secret_access_service)
):
    await service.revoke_access(tenant_id, secret_id, principal_id)
