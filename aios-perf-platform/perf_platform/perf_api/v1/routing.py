"""LLM Cost-Intelligence Model Routing: policy management + tier
selection with cost estimation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from perf_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_model_routing_service,
    get_routing_policy_service,
)
from perf_platform.perf_api.serialization import to_dict, to_dict_list
from perf_platform.routing.routing_service import ModelRoutingService, RoutingPolicyService

router = APIRouter(prefix="/routing", tags=["routing"])


class SetRoutingPolicyRequest(BaseModel):
    scope_type: str
    scope_id: str
    allowed_tiers: list[str]
    default_tier: str = "medium"
    max_cost_per_request_usd: float | None = None


@router.put("/policies")
async def set_policy(
    body: SetRoutingPolicyRequest, tenant_id: str = Depends(get_current_tenant_id), service: RoutingPolicyService = Depends(get_routing_policy_service),
):
    return to_dict(await service.set_policy(tenant_id, **body.model_dump()))


class RouteRequest(BaseModel):
    task_complexity: str
    user_tier: str = "enterprise"
    latency_budget_ms: float | None = None
    requires_vision: bool = False
    requires_code: bool = False
    policy_scope_type: str | None = None
    policy_scope_id: str | None = None
    estimated_input_tokens: int = 500
    estimated_output_tokens: int = 500


@router.post("/route")
async def route(
    body: RouteRequest, tenant_id: str = Depends(get_current_tenant_id), service: ModelRoutingService = Depends(get_model_routing_service),
):
    return to_dict(await service.route(tenant_id, **body.model_dump()))


@router.get("/decisions")
async def recent_decisions(
    tenant_id: str = Depends(get_current_tenant_id), service: ModelRoutingService = Depends(get_model_routing_service),
):
    return to_dict_list(await service.recent_decisions(tenant_id))
