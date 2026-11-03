"""Infra Security & Governance API: network policies, runtime
policies, and ordered infra RBAC role bindings."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_infra_role_binding_service,
    get_network_policy_service,
    get_runtime_policy_service,
)
from infra_platform.infra_api.serialization import to_dict, to_dict_list
from infra_platform.infra_security.security_service import InfraRoleBindingService, NetworkPolicyService, RuntimePolicyService

router = APIRouter(prefix="/infra-security", tags=["infra-security"])


class CreateNetworkPolicyRequest(BaseModel):
    name: str
    cluster_id: str | None = None
    namespace: str | None = None
    rules: dict | None = None


@router.post("/network-policies", status_code=201)
async def create_network_policy(body: CreateNetworkPolicyRequest, tenant_id: str = Depends(get_current_tenant_id), service: NetworkPolicyService = Depends(get_network_policy_service)):
    return to_dict(await service.create_policy(tenant_id, **body.model_dump()))


@router.get("/network-policies")
async def list_network_policies(tenant_id: str = Depends(get_current_tenant_id), service: NetworkPolicyService = Depends(get_network_policy_service)):
    return to_dict_list(await service.list_enabled(tenant_id))


@router.post("/network-policies/{policy_id}/disable")
async def disable_network_policy(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: NetworkPolicyService = Depends(get_network_policy_service)):
    return to_dict(await service.disable(tenant_id, policy_id))


@router.post("/network-policies/{policy_id}/enable")
async def enable_network_policy(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: NetworkPolicyService = Depends(get_network_policy_service)):
    return to_dict(await service.enable(tenant_id, policy_id))


class EvaluateConnectionRequest(BaseModel):
    destination: str


@router.post("/network-policies/evaluate")
async def evaluate_connection(body: EvaluateConnectionRequest, tenant_id: str = Depends(get_current_tenant_id), service: NetworkPolicyService = Depends(get_network_policy_service)):
    return {"allowed": await service.evaluate_connection(tenant_id, **body.model_dump())}


class CreateRuntimePolicyRequest(BaseModel):
    name: str
    policy_type: str
    rules: dict | None = None


@router.post("/runtime-policies", status_code=201)
async def create_runtime_policy(body: CreateRuntimePolicyRequest, tenant_id: str = Depends(get_current_tenant_id), service: RuntimePolicyService = Depends(get_runtime_policy_service)):
    return to_dict(await service.create_policy(tenant_id, **body.model_dump()))


@router.get("/runtime-policies")
async def list_runtime_policies(tenant_id: str = Depends(get_current_tenant_id), service: RuntimePolicyService = Depends(get_runtime_policy_service)):
    return to_dict_list(await service.list_enabled(tenant_id))


@router.post("/runtime-policies/{policy_id}/disable")
async def disable_runtime_policy(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RuntimePolicyService = Depends(get_runtime_policy_service)):
    return to_dict(await service.disable(tenant_id, policy_id))


@router.post("/runtime-policies/{policy_id}/enable")
async def enable_runtime_policy(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RuntimePolicyService = Depends(get_runtime_policy_service)):
    return to_dict(await service.enable(tenant_id, policy_id))


class EvaluateRuntimeRequest(BaseModel):
    context: dict


@router.post("/runtime-policies/evaluate")
async def evaluate_runtime(body: EvaluateRuntimeRequest, tenant_id: str = Depends(get_current_tenant_id), service: RuntimePolicyService = Depends(get_runtime_policy_service)):
    return {"allowed": await service.evaluate(tenant_id, **body.model_dump())}


class GrantRoleRequest(BaseModel):
    principal_id: str
    role: str
    scope: str | None = None


@router.post("/roles/grant", status_code=201)
async def grant_role(body: GrantRoleRequest, tenant_id: str = Depends(get_current_tenant_id), service: InfraRoleBindingService = Depends(get_infra_role_binding_service)):
    return to_dict(await service.grant_role(tenant_id, **body.model_dump()))


class RevokeRoleRequest(BaseModel):
    principal_id: str
    scope: str | None = None


@router.post("/roles/revoke", status_code=204)
async def revoke_role(body: RevokeRoleRequest, tenant_id: str = Depends(get_current_tenant_id), service: InfraRoleBindingService = Depends(get_infra_role_binding_service)):
    await service.revoke_role(tenant_id, **body.model_dump())


@router.get("/roles/{principal_id}")
async def list_role_bindings(principal_id: str, tenant_id: str = Depends(get_current_tenant_id), service: InfraRoleBindingService = Depends(get_infra_role_binding_service)):
    return to_dict_list(await service.list_for_principal(tenant_id, principal_id))
