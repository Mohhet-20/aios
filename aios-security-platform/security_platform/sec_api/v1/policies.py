"""Policy Engine API: CRUD, lifecycle transitions, version history,
time-boxed exceptions, and evaluation."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import (
    get_current_actor_id,
    get_current_tenant_id,
    get_policy_evaluation_service,
    get_policy_exception_service,
    get_policy_service,
)
from security_platform.policies.evaluation_service import PolicyDecision, PolicyEvaluationService
from security_platform.policies.exception_service import PolicyExceptionService
from security_platform.policies.policy_service import PolicyService
from security_platform.sec_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/policies", tags=["policies"])


class CreatePolicyRequest(BaseModel):
    name: str
    scope: str
    effect: str = "deny"
    rules: dict | None = None
    scope_ref_id: str | None = None
    parent_policy_id: str | None = None
    priority: int = 100
    description: str | None = None


@router.post("", status_code=201)
async def create_policy(
    body: CreatePolicyRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: PolicyService = Depends(get_policy_service),
):
    return to_dict(await service.create_policy(tenant_id, **body.model_dump(), created_by=actor_id))


class UpdateRulesRequest(BaseModel):
    rules: dict
    effect: str | None = None


@router.patch("/{policy_id}/rules")
async def update_rules(
    policy_id: str, body: UpdateRulesRequest, tenant_id: str = Depends(get_current_tenant_id),
    actor_id: str | None = Depends(get_current_actor_id), service: PolicyService = Depends(get_policy_service),
):
    return to_dict(await service.update_rules(tenant_id, policy_id, rules=body.rules, effect=body.effect, updated_by=actor_id))


@router.post("/{policy_id}/activate")
async def activate(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PolicyService = Depends(get_policy_service)):
    return to_dict(await service.activate(tenant_id, policy_id))


@router.post("/{policy_id}/deprecate")
async def deprecate(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PolicyService = Depends(get_policy_service)):
    return to_dict(await service.deprecate(tenant_id, policy_id))


@router.post("/{policy_id}/archive")
async def archive(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PolicyService = Depends(get_policy_service)):
    return to_dict(await service.archive(tenant_id, policy_id))


@router.get("")
async def list_for_scope(
    scope: str, scope_ref_id: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: PolicyService = Depends(get_policy_service),
):
    return to_dict_list(await service.list_for_scope(tenant_id, scope, scope_ref_id=scope_ref_id))


@router.get("/{policy_id}/history")
async def history(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PolicyService = Depends(get_policy_service)):
    return to_dict_list(await service.history(tenant_id, policy_id))


class GrantExceptionRequest(BaseModel):
    policy_id: str
    scope_ref_id: str
    reason: str
    expires_at: datetime


@router.post("/exceptions", status_code=201)
async def grant_exception(
    body: GrantExceptionRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: PolicyExceptionService = Depends(get_policy_exception_service),
):
    return to_dict(
        await service.grant_exception(
            tenant_id, body.policy_id, body.scope_ref_id, reason=body.reason, expires_at=body.expires_at, granted_by=actor_id
        )
    )


@router.delete("/exceptions/{exception_id}", status_code=204)
async def revoke_exception(
    exception_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PolicyExceptionService = Depends(get_policy_exception_service),
):
    await service.revoke_exception(tenant_id, exception_id)


@router.get("/evaluate")
async def evaluate(
    scope: str, scope_ref_id: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: PolicyEvaluationService = Depends(get_policy_evaluation_service),
) -> PolicyDecision:
    return await service.evaluate(tenant_id, scope, scope_ref_id=scope_ref_id)
