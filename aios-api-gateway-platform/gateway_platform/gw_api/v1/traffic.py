"""Traffic Management: routing rules per route."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import get_current_tenant_id, get_traffic_rule_service
from gateway_platform.gw_api.serialization import to_dict, to_dict_list
from gateway_platform.traffic.traffic_rule_service import TrafficRuleService

router = APIRouter(prefix="/traffic-rules", tags=["traffic-management"])


class CreateTrafficRuleRequest(BaseModel):
    route_id: str
    rule_type: str
    config: dict
    priority: int = 0


@router.post("", status_code=201)
async def create_traffic_rule(
    body: CreateTrafficRuleRequest, tenant_id: str = Depends(get_current_tenant_id), service: TrafficRuleService = Depends(get_traffic_rule_service),
):
    return to_dict(await service.create_rule(tenant_id, body.route_id, rule_type=body.rule_type, config=body.config, priority=body.priority))


@router.get("/for-route/{route_id}")
async def list_traffic_rules(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TrafficRuleService = Depends(get_traffic_rule_service),
):
    return to_dict_list(await service.list_for_route(tenant_id, route_id))


@router.post("/{rule_id}/activate")
async def activate_traffic_rule(
    rule_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TrafficRuleService = Depends(get_traffic_rule_service),
):
    return to_dict(await service.activate_rule(tenant_id, rule_id))


@router.post("/{rule_id}/deactivate")
async def deactivate_traffic_rule(
    rule_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TrafficRuleService = Depends(get_traffic_rule_service),
):
    return to_dict(await service.deactivate_rule(tenant_id, rule_id))


class ResolveDestinationRequest(BaseModel):
    route_id: str
    context: dict | None = None
    default: str | None = None


@router.post("/resolve")
async def resolve_destination(
    body: ResolveDestinationRequest, tenant_id: str = Depends(get_current_tenant_id), service: TrafficRuleService = Depends(get_traffic_rule_service),
):
    destination = await service.resolve_destination(tenant_id, body.route_id, context=body.context, default=body.default)
    return {"destination": destination}
