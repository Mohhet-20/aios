"""Dashboards API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dashboards.dashboard_service import DashboardService
from observability_platform.dependencies.dependencies import get_current_tenant_id, get_dashboard_service
from observability_platform.obs_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


class CreateDashboardRequest(BaseModel):
    name: str
    dashboard_type: str
    owner: str | None = None
    layout: dict | None = None
    widgets: list | None = None
    is_default: bool = False


@router.post("", status_code=201)
async def create_dashboard(body: CreateDashboardRequest, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service)):
    return to_dict(await service.create_dashboard(tenant_id, **body.model_dump()))


@router.get("")
async def list_dashboards(tenant_id: str = Depends(get_current_tenant_id), dashboard_type: str | None = None, service: DashboardService = Depends(get_dashboard_service)):
    return to_dict_list(await service.list_dashboards(tenant_id, dashboard_type=dashboard_type))


class UpdateWidgetsRequest(BaseModel):
    widgets: list


@router.put("/{dashboard_id}/widgets")
async def update_widgets(dashboard_id: str, body: UpdateWidgetsRequest, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service)):
    return to_dict(await service.update_widgets(tenant_id, dashboard_id, body.widgets))


@router.get("/{dashboard_id}/render")
async def render_dashboard(dashboard_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service)):
    return await service.render(tenant_id, dashboard_id)
