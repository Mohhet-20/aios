"""API Platform: key issuance/auth, rate limiting, versioning."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.api_platform.api_key_service import ApiKeyService
from developer_platform.api_platform.rate_limit_service import RateLimiterService
from developer_platform.api_platform.version_service import ApiVersionService
from developer_platform.dependencies.dependencies import (
    get_api_key_service,
    get_api_version_service,
    get_current_tenant_id,
    get_rate_limiter_service,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/api-keys", tags=["api-platform"])


class IssueApiKeyRequest(BaseModel):
    name: str
    scopes: list[str] = []
    rate_limit_per_minute: int | None = None
    ttl_days: int | None = None


@router.post("", status_code=201)
async def issue_api_key(
    body: IssueApiKeyRequest, tenant_id: str = Depends(get_current_tenant_id), service: ApiKeyService = Depends(get_api_key_service),
):
    result = await service.issue_key(tenant_id, **body.model_dump())
    return {"api_key": to_dict(result.api_key), "raw_key": result.raw_key}


@router.get("")
async def list_api_keys(tenant_id: str = Depends(get_current_tenant_id), service: ApiKeyService = Depends(get_api_key_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/{api_key_id}/revoke")
async def revoke_api_key(api_key_id: str, service: ApiKeyService = Depends(get_api_key_service)):
    return to_dict(await service.revoke_key(api_key_id))


@router.post("/{api_key_id}/rotate")
async def rotate_api_key(api_key_id: str, service: ApiKeyService = Depends(get_api_key_service)):
    result = await service.rotate_key(api_key_id)
    return {"api_key": to_dict(result.api_key), "raw_key": result.raw_key}


class VerifyApiKeyRequest(BaseModel):
    raw_key: str


@router.post("/verify")
async def verify_api_key(body: VerifyApiKeyRequest, service: ApiKeyService = Depends(get_api_key_service)):
    return to_dict(await service.verify_key(body.raw_key))


usage_router = APIRouter(prefix="/api-usage", tags=["api-platform"])


class RecordUsageRequest(BaseModel):
    api_key_id: str | None = None
    endpoint: str
    method: str
    status_code: int = 200
    latency_ms: float = 0.0


@usage_router.post("/record")
async def record_usage(
    body: RecordUsageRequest, tenant_id: str = Depends(get_current_tenant_id), service: RateLimiterService = Depends(get_rate_limiter_service),
):
    return to_dict(await service.record(tenant_id, **body.model_dump()))


versions_router = APIRouter(prefix="/api-versions", tags=["api-platform"])


class RegisterApiVersionRequest(BaseModel):
    version: str
    notes: str | None = None


@versions_router.post("", status_code=201)
async def register_api_version(body: RegisterApiVersionRequest, service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict(await service.register_version(**body.model_dump()))


@versions_router.get("")
async def list_api_versions(service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict_list(await service.list_versions())


@versions_router.post("/{version}/deprecate")
async def deprecate_api_version(version: str, service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict(await service.deprecate_version(version))


@versions_router.post("/{version}/sunset")
async def sunset_api_version(version: str, service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict(await service.sunset_version(version))
