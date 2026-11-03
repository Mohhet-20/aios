"""Developer Analytics & Observability: sampled usage-event recording
and activity dashboards. `record_event` returns 204 when the event was
sampled out (the service returns `None` by design when the sample
rate excludes it), never an error."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_dashboard_service,
    get_usage_analytics_service,
)
from developer_platform.developer_analytics.dashboard_service import DeveloperActivityDashboardService
from developer_platform.developer_analytics.usage_service import UsageAnalyticsService
from developer_platform.dev_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/analytics/usage-events", tags=["developer-analytics"])


class RecordEventRequest(BaseModel):
    event_type: str
    resource_type: str | None = None
    resource_id: str | None = None
    developer_id: str | None = None
    metadata: dict | None = None


@router.post("", status_code=201)
async def record_usage_event(
    body: RecordEventRequest, response: Response, tenant_id: str = Depends(get_current_tenant_id),
    service: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    event = await service.record_event(tenant_id, body.event_type, **body.model_dump(exclude={"event_type"}))
    if event is None:
        response.status_code = 204
        return None
    return to_dict(event)


@router.get("/summary")
async def get_usage_summary(
    tenant_id: str = Depends(get_current_tenant_id), service: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    return await service.get_summary(tenant_id)


@router.get("")
async def list_recent_usage_events(
    event_type: str | None = None, limit: int = 200, tenant_id: str = Depends(get_current_tenant_id),
    service: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    return to_dict_list(await service.list_recent(tenant_id, event_type=event_type, limit=limit))


dashboard_router = APIRouter(prefix="/analytics/dashboard", tags=["developer-analytics"])


@dashboard_router.get("/summary")
async def get_dashboard_summary(
    tenant_id: str = Depends(get_current_tenant_id), service: DeveloperActivityDashboardService = Depends(get_dashboard_service),
):
    return await service.build_summary(tenant_id)


@dashboard_router.get("/top-resources")
async def get_top_resources(
    event_type: str | None = None, limit: int = 10, window: int = 1000, tenant_id: str = Depends(get_current_tenant_id),
    service: DeveloperActivityDashboardService = Depends(get_dashboard_service),
):
    pairs = await service.top_resources(tenant_id, event_type=event_type, limit=limit, window=window)
    return [{"resource_id": rid, "count": count} for rid, count in pairs]


@dashboard_router.get("/most-active-developers")
async def get_most_active_developers(
    event_type: str | None = None, limit: int = 10, window: int = 1000, tenant_id: str = Depends(get_current_tenant_id),
    service: DeveloperActivityDashboardService = Depends(get_dashboard_service),
):
    pairs = await service.most_active_developers(tenant_id, event_type=event_type, limit=limit, window=window)
    return [{"developer_id": did, "count": count} for did, count in pairs]
