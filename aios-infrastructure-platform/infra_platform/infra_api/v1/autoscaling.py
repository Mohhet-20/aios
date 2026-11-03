"""Generic Autoscaling API: scaling policies (horizontal/vertical/
cluster/GPU/queue-based/predictive/cost-aware) and cooldown-gated
scale evaluation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.autoscaling.autoscaling_service import ScalingPolicyService
from infra_platform.dependencies.dependencies import get_current_tenant_id, get_scaling_policy_service
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/autoscaling", tags=["autoscaling"])


class CreatePolicyRequest(BaseModel):
    resource_type: str
    resource_id: str
    policy_type: str
    min_capacity: int = 1
    max_capacity: int = 10
    target_metric: str | None = None
    target_value: float | None = None


@router.post("/policies", status_code=201)
async def create_policy(body: CreatePolicyRequest, tenant_id: str = Depends(get_current_tenant_id), service: ScalingPolicyService = Depends(get_scaling_policy_service)):
    return to_dict(await service.create_policy(tenant_id, **body.model_dump()))


@router.get("/policies")
async def list_policies(resource_type: str, resource_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ScalingPolicyService = Depends(get_scaling_policy_service)):
    return to_dict_list(await service.list_for_resource(tenant_id, resource_type, resource_id))


class SetEnabledRequest(BaseModel):
    enabled: bool


@router.patch("/policies/{policy_id}/enabled")
async def set_enabled(policy_id: str, body: SetEnabledRequest, tenant_id: str = Depends(get_current_tenant_id), service: ScalingPolicyService = Depends(get_scaling_policy_service)):
    return to_dict(await service.set_enabled(tenant_id, policy_id, **body.model_dump()))


class EvaluateScaleRequest(BaseModel):
    current_capacity: int
    desired_capacity: int
    reason: str | None = None


@router.post("/policies/{policy_id}/evaluate")
async def evaluate_scale(policy_id: str, body: EvaluateScaleRequest, tenant_id: str = Depends(get_current_tenant_id), service: ScalingPolicyService = Depends(get_scaling_policy_service)):
    return to_dict(await service.evaluate_scale(tenant_id, policy_id, **body.model_dump()))


@router.get("/policies/{policy_id}/events")
async def list_events(policy_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ScalingPolicyService = Depends(get_scaling_policy_service)):
    return to_dict_list(await service.list_events(tenant_id, policy_id))
