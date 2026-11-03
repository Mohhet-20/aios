"""Visualization & Dashboard Platform: dashboards, widgets, and saved
views (self-service filter/layout presets)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dashboards.dashboard_service import DashboardService
from analytics_platform.dashboards.saved_view_service import SavedViewService
from analytics_platform.dependencies.dependencies import get_current_tenant_id, get_dashboard_service, get_saved_view_service

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


class CreateDashboardRequest(BaseModel):
    name: str
    description: str | None = None
    owner_id: str | None = None
    visibility: str = "private"
    layout: dict | None = None


@router.post("", status_code=201)
async def create_dashboard(
    body: CreateDashboardRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict(await service.create_dashboard(tenant_id, **body.model_dump()))


@router.get("")
async def list_dashboards(
    status: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, status=status))


@router.get("/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict(await service.get_or_404(tenant_id, dashboard_id))


class UpdateLayoutRequest(BaseModel):
    layout: dict


@router.put("/{dashboard_id}/layout")
async def update_layout(
    dashboard_id: str, body: UpdateLayoutRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict(await service.update_layout(tenant_id, dashboard_id, body.layout))


@router.post("/{dashboard_id}/publish")
async def publish_dashboard(
    dashboard_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict(await service.publish(tenant_id, dashboard_id))


@router.post("/{dashboard_id}/archive")
async def archive_dashboard(
    dashboard_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict(await service.archive(tenant_id, dashboard_id))


@router.post("/{dashboard_id}/republish")
async def republish_dashboard(
    dashboard_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict(await service.republish(tenant_id, dashboard_id))


class AddWidgetRequest(BaseModel):
    visualization_type: str
    title: str
    query_config: dict | None = None
    position: dict | None = None


@router.post("/{dashboard_id}/widgets", status_code=201)
async def add_widget(
    dashboard_id: str, body: AddWidgetRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict(await service.add_widget(tenant_id, dashboard_id, **body.model_dump()))


@router.get("/{dashboard_id}/widgets")
async def list_widgets(
    dashboard_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DashboardService = Depends(get_dashboard_service),
):
    return to_dict_list(await service.list_widgets(tenant_id, dashboard_id))


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def remove_widget(
    dashboard_id: str, widget_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(get_dashboard_service),
):
    await service.remove_widget(tenant_id, dashboard_id, widget_id)


class CreateSavedViewRequest(BaseModel):
    name: str
    owner_id: str | None = None
    filters: dict | None = None


@router.post("/{dashboard_id}/saved-views", status_code=201)
async def create_saved_view(
    dashboard_id: str, body: CreateSavedViewRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: SavedViewService = Depends(get_saved_view_service),
):
    return to_dict(await service.create_saved_view(tenant_id, dashboard_id, **body.model_dump()))


@router.get("/{dashboard_id}/saved-views")
async def list_saved_views(
    dashboard_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SavedViewService = Depends(get_saved_view_service),
):
    return to_dict_list(await service.list_for_dashboard(tenant_id, dashboard_id))


@router.delete("/{dashboard_id}/saved-views/{view_id}", status_code=204)
async def delete_saved_view(
    dashboard_id: str, view_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: SavedViewService = Depends(get_saved_view_service),
):
    await service.delete_saved_view(tenant_id, dashboard_id, view_id)
