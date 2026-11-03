"""API keys, service accounts (machine identities), and webhook
signing secrets."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.api_keys.api_key_service import ApiKeyService
from identity_platform.api_keys.service_account_service import ServiceAccountService
from identity_platform.api_keys.webhook_secret_service import WebhookSecretService
from identity_platform.dependencies.dependencies import (
    get_api_key_service,
    get_service_account_service,
    get_webhook_secret_service,
)
from identity_platform.identity_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class IssueApiKeyRequest(BaseModel):
    organization_id: str
    owner_type: str
    owner_id: str
    name: str
    created_by: str
    scopes: list[str] = []
    workspace_id: str | None = None


@router.post("", status_code=201)
async def issue_api_key(body: IssueApiKeyRequest, service: ApiKeyService = Depends(get_api_key_service)):
    result = await service.issue_key(
        body.organization_id, owner_type=body.owner_type, owner_id=body.owner_id, name=body.name,
        created_by=body.created_by, scopes=body.scopes, workspace_id=body.workspace_id,
    )
    return {"api_key": to_dict(result.api_key), "raw_key": result.raw_key}


class VerifyApiKeyRequest(BaseModel):
    raw_key: str


@router.post("/verify")
async def verify_api_key(body: VerifyApiKeyRequest, service: ApiKeyService = Depends(get_api_key_service)):
    return to_dict(await service.verify_key(body.raw_key))


@router.post("/{api_key_id}/revoke")
async def revoke_api_key(api_key_id: str, service: ApiKeyService = Depends(get_api_key_service)):
    return to_dict(await service.revoke_key(api_key_id))


@router.post("/{api_key_id}/rotate")
async def rotate_api_key(api_key_id: str, service: ApiKeyService = Depends(get_api_key_service)):
    result = await service.rotate_key(api_key_id)
    return {"api_key": to_dict(result.api_key), "raw_key": result.raw_key}


@router.get("/owners/{owner_type}/{owner_id}")
async def list_api_keys_for_owner(owner_type: str, owner_id: str, service: ApiKeyService = Depends(get_api_key_service)):
    return to_dict_list(await service.list_for_owner(owner_type, owner_id))


class CreateServiceAccountRequest(BaseModel):
    organization_id: str
    name: str
    description: str | None = None


@router.post("/service-accounts", status_code=201)
async def create_service_account(body: CreateServiceAccountRequest, service: ServiceAccountService = Depends(get_service_account_service)):
    return to_dict(await service.create(body.organization_id, name=body.name, description=body.description))


@router.post("/service-accounts/{service_account_id}/disable")
async def disable_service_account(service_account_id: str, service: ServiceAccountService = Depends(get_service_account_service)):
    return to_dict(await service.disable(service_account_id))


@router.post("/service-accounts/{service_account_id}/enable")
async def enable_service_account(service_account_id: str, service: ServiceAccountService = Depends(get_service_account_service)):
    return to_dict(await service.enable(service_account_id))


@router.get("/service-accounts")
async def list_service_accounts(organization_id: str, service: ServiceAccountService = Depends(get_service_account_service)):
    return to_dict_list(await service.list_for_organization(organization_id))


class CreateWebhookSecretRequest(BaseModel):
    organization_id: str
    name: str


@router.post("/webhook-secrets", status_code=201)
async def create_webhook_secret(body: CreateWebhookSecretRequest, service: WebhookSecretService = Depends(get_webhook_secret_service)):
    secret, raw_secret = await service.create_secret(body.organization_id, name=body.name)
    return {"secret": to_dict(secret), "raw_secret": raw_secret}


@router.post("/webhook-secrets/{secret_id}/rotate")
async def rotate_webhook_secret(secret_id: str, service: WebhookSecretService = Depends(get_webhook_secret_service)):
    secret, raw_secret = await service.rotate_secret(secret_id)
    return {"secret": to_dict(secret), "raw_secret": raw_secret}


@router.get("/webhook-secrets")
async def list_webhook_secrets(organization_id: str, service: WebhookSecretService = Depends(get_webhook_secret_service)):
    return to_dict_list(await service.list_for_organization(organization_id))
