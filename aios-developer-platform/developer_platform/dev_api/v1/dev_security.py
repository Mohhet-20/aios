"""Developer Platform security: RBAC role bindings, opaque secret
references (never raw secrets — see `SecretReferenceService`
docstring), plugin isolation policy evaluation, and OAuth scope
negotiation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_oauth_readiness_service,
    get_plugin_isolation_service,
    get_rbac_service,
    get_secret_reference_service,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list
from developer_platform.dev_security.oauth_readiness_service import OAuthReadinessService
from developer_platform.dev_security.plugin_isolation_service import PluginIsolationService
from developer_platform.dev_security.rbac_service import DeveloperRbacService
from developer_platform.dev_security.secret_reference_service import SecretReferenceService

router = APIRouter(prefix="/security/rbac", tags=["dev-security"])


class GrantRoleRequest(BaseModel):
    principal_id: str
    role: str
    scope: str | None = None


@router.post("/grant", status_code=201)
async def grant_developer_role(
    body: GrantRoleRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeveloperRbacService = Depends(get_rbac_service),
):
    return to_dict(await service.grant_role(tenant_id, **body.model_dump()))


@router.get("/for-principal/{principal_id}")
async def list_roles_for_principal(
    principal_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeveloperRbacService = Depends(get_rbac_service),
):
    return to_dict_list(await service.list_for_principal(tenant_id, principal_id))


secrets_router = APIRouter(prefix="/security/secrets", tags=["dev-security"])


class IssueSecretReferenceRequest(BaseModel):
    name: str
    reference_type: str


@secrets_router.post("", status_code=201)
async def issue_secret_reference(
    body: IssueSecretReferenceRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: SecretReferenceService = Depends(get_secret_reference_service),
):
    return to_dict(await service.issue_reference(tenant_id, **body.model_dump()))


@secrets_router.post("/{reference_id}/rotate")
async def rotate_secret_reference(reference_id: str, service: SecretReferenceService = Depends(get_secret_reference_service)):
    return to_dict(await service.rotate_reference(reference_id))


@secrets_router.get("/by-type/{reference_type}")
async def list_secret_references_by_type(
    reference_type: str, tenant_id: str = Depends(get_current_tenant_id),
    service: SecretReferenceService = Depends(get_secret_reference_service),
):
    return to_dict_list(await service.list_by_type(tenant_id, reference_type))


isolation_router = APIRouter(prefix="/security/plugin-isolation", tags=["dev-security"])


class EvaluateIsolationRequest(BaseModel):
    manifest_permissions: list[str]
    allowed_permissions: list[str] | None = None
    denied_permissions: list[str] | None = None


@isolation_router.post("/evaluate")
async def evaluate_plugin_isolation(body: EvaluateIsolationRequest, service: PluginIsolationService = Depends(get_plugin_isolation_service)):
    decision = service.evaluate(
        body.manifest_permissions, allowed_permissions=body.allowed_permissions, denied_permissions=body.denied_permissions,
    )
    return {"allowed": decision.allowed, "violations": decision.violations}


oauth_router = APIRouter(prefix="/security/oauth", tags=["dev-security"])


class ScopesRequest(BaseModel):
    requested: list[str]
    granted: list[str]


@oauth_router.post("/validate-scopes")
async def validate_oauth_scopes(body: ScopesRequest, service: OAuthReadinessService = Depends(get_oauth_readiness_service)):
    service.validate_scopes(body.requested, body.granted)
    return {"valid": True}


@oauth_router.post("/narrow-scopes")
async def narrow_oauth_scopes(body: ScopesRequest, service: OAuthReadinessService = Depends(get_oauth_readiness_service)):
    return {"scopes": service.narrow_scopes(body.requested, body.granted)}
