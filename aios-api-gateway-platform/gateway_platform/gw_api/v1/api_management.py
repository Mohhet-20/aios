"""API Management: keys, usage/rate limiting, versions, JWT, OAuth
clients, request/response schemas."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.api_management.api_key_service import ApiKeyService
from gateway_platform.api_management.jwt_service import JwtService
from gateway_platform.api_management.oauth_client_service import OAuthClientService
from gateway_platform.api_management.rate_limit_service import RateLimiterService
from gateway_platform.api_management.schema_service import SchemaValidationService
from gateway_platform.api_management.version_service import ApiVersionService
from gateway_platform.dependencies.dependencies import (
    get_api_key_service,
    get_api_version_service,
    get_current_tenant_id,
    get_jwt_service,
    get_oauth_client_service,
    get_rate_limiter_service,
    get_schema_validation_service,
)
from gateway_platform.gw_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/api-keys", tags=["api-management"])


class IssueApiKeyRequest(BaseModel):
    name: str
    scopes: list[str] | None = None
    rate_limit_per_minute: int | None = None
    quota_per_day: int | None = None
    ttl_days: int | None = None


@router.post("", status_code=201)
async def issue_api_key(
    body: IssueApiKeyRequest, tenant_id: str = Depends(get_current_tenant_id), service: ApiKeyService = Depends(get_api_key_service),
):
    result = await service.issue_key(tenant_id, **body.model_dump())
    return {"api_key": to_dict(result.api_key), "raw_key": result.raw_key}


class VerifyApiKeyRequest(BaseModel):
    raw_key: str


@router.post("/verify")
async def verify_api_key(body: VerifyApiKeyRequest, service: ApiKeyService = Depends(get_api_key_service)):
    return to_dict(await service.verify_key(body.raw_key))


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


usage_router = APIRouter(prefix="/api-usage", tags=["api-management"])


class RecordUsageRequest(BaseModel):
    api_key_id: str | None = None
    route_id: str | None = None
    endpoint: str
    method: str
    status_code: int = 200
    latency_ms: float = 0.0


@usage_router.post("/record")
async def record_api_usage(
    body: RecordUsageRequest, tenant_id: str = Depends(get_current_tenant_id), service: RateLimiterService = Depends(get_rate_limiter_service),
):
    return to_dict(await service.record(tenant_id, **body.model_dump()))


versions_router = APIRouter(prefix="/api-versions", tags=["api-management"])


class RegisterVersionRequest(BaseModel):
    version: str
    notes: str | None = None


@versions_router.post("", status_code=201)
async def register_api_version(body: RegisterVersionRequest, service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict(await service.register_version(body.version, notes=body.notes))


@versions_router.get("")
async def list_api_versions(service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict_list(await service.list_versions())


@versions_router.post("/{version}/deprecate")
async def deprecate_api_version(version: str, service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict(await service.deprecate_version(version))


@versions_router.post("/{version}/retire")
async def retire_api_version(version: str, service: ApiVersionService = Depends(get_api_version_service)):
    return to_dict(await service.retire_version(version))


jwt_router = APIRouter(prefix="/jwt", tags=["api-management"])


class IssueJwtRequest(BaseModel):
    subject: str
    scopes: list[str] | None = None
    ttl_minutes: int | None = None


@jwt_router.post("/issue")
async def issue_jwt(
    body: IssueJwtRequest, tenant_id: str = Depends(get_current_tenant_id), service: JwtService = Depends(get_jwt_service),
):
    token = service.issue_token(subject=body.subject, tenant_id=tenant_id, scopes=body.scopes, ttl_minutes=body.ttl_minutes)
    return {"token": token}


class ValidateJwtRequest(BaseModel):
    token: str


@jwt_router.post("/validate")
async def validate_jwt(body: ValidateJwtRequest, service: JwtService = Depends(get_jwt_service)):
    return service.validate_token(body.token)


oauth_router = APIRouter(prefix="/oauth-clients", tags=["api-management"])


class RegisterOAuthClientRequest(BaseModel):
    name: str
    redirect_uris: list[str] | None = None
    scopes: list[str] | None = None


@oauth_router.post("", status_code=201)
async def register_oauth_client(
    body: RegisterOAuthClientRequest, tenant_id: str = Depends(get_current_tenant_id), service: OAuthClientService = Depends(get_oauth_client_service),
):
    client, secret = await service.register_client(tenant_id, **body.model_dump())
    return {"client": to_dict(client), "client_secret": secret}


@oauth_router.get("")
async def list_oauth_clients(tenant_id: str = Depends(get_current_tenant_id), service: OAuthClientService = Depends(get_oauth_client_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@oauth_router.post("/{client_id}/suspend")
async def suspend_oauth_client(client_id: str, service: OAuthClientService = Depends(get_oauth_client_service)):
    return to_dict(await service.suspend_client(client_id))


@oauth_router.post("/{client_id}/revoke")
async def revoke_oauth_client(client_id: str, service: OAuthClientService = Depends(get_oauth_client_service)):
    return to_dict(await service.revoke_client(client_id))


schemas_router = APIRouter(prefix="/api-schemas", tags=["api-management"])


class RegisterSchemaRequest(BaseModel):
    route_id: str
    schema_kind: str
    json_schema: dict


@schemas_router.post("", status_code=201)
async def register_schema(
    body: RegisterSchemaRequest, tenant_id: str = Depends(get_current_tenant_id), service: SchemaValidationService = Depends(get_schema_validation_service),
):
    return to_dict(await service.register_schema(tenant_id, body.route_id, schema_kind=body.schema_kind, json_schema=body.json_schema))


class ValidatePayloadRequest(BaseModel):
    route_id: str
    schema_kind: str
    payload: dict


@schemas_router.post("/validate")
async def validate_payload(
    body: ValidatePayloadRequest, tenant_id: str = Depends(get_current_tenant_id), service: SchemaValidationService = Depends(get_schema_validation_service),
):
    await service.validate_payload(tenant_id, body.route_id, schema_kind=body.schema_kind, payload=body.payload)
    return {"valid": True}


@schemas_router.get("/for-route/{route_id}")
async def list_schemas_for_route(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SchemaValidationService = Depends(get_schema_validation_service),
):
    return to_dict_list(await service.list_for_route(tenant_id, route_id))
