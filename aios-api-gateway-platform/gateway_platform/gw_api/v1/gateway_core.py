"""Gateway Core: the route registry every inbound request is matched
against."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import get_current_tenant_id, get_route_service
from gateway_platform.gateway_core.route_service import RouteRegistrationService
from gateway_platform.gw_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/routes", tags=["gateway-core"])


class RegisterRouteRequest(BaseModel):
    path: str
    method: str = "GET"
    protocol: str = "rest"
    visibility: str = "internal"
    target_service: str
    description: str | None = None
    timeout_ms: int | None = None
    tags: list[str] | None = None


@router.post("", status_code=201)
async def register_route(
    body: RegisterRouteRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: RouteRegistrationService = Depends(get_route_service),
):
    return to_dict(await service.register_route(tenant_id, **body.model_dump()))


@router.get("")
async def list_routes(
    status: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: RouteRegistrationService = Depends(get_route_service),
):
    return to_dict_list(await service.list_routes(tenant_id, status=status))


@router.get("/match")
async def match_route(
    path: str, method: str, tenant_id: str = Depends(get_current_tenant_id),
    service: RouteRegistrationService = Depends(get_route_service),
):
    return to_dict(await service.match_route(tenant_id, path, method))


@router.post("/{route_id}/activate")
async def activate_route(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RouteRegistrationService = Depends(get_route_service),
):
    return to_dict(await service.activate_route(tenant_id, route_id))


@router.post("/{route_id}/deprecate")
async def deprecate_route(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RouteRegistrationService = Depends(get_route_service),
):
    return to_dict(await service.deprecate_route(tenant_id, route_id))


@router.post("/{route_id}/reactivate")
async def reactivate_route(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RouteRegistrationService = Depends(get_route_service),
):
    return to_dict(await service.reactivate_route(tenant_id, route_id))


@router.post("/{route_id}/retire")
async def retire_route(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RouteRegistrationService = Depends(get_route_service),
):
    return to_dict(await service.retire_route(tenant_id, route_id))
