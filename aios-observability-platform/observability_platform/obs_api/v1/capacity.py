"""Capacity planning API: snapshots, forecasts, scaling
recommendations."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.capacity.forecast_service import CapacityForecastService
from observability_platform.dependencies.dependencies import get_capacity_forecast_service, get_current_tenant_id
from observability_platform.obs_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/capacity", tags=["capacity"])


class RecordSnapshotRequest(BaseModel):
    resource_type: str
    value: float
    unit: str | None = None
    component_id: str | None = None


@router.post("/snapshots", status_code=201)
async def record_snapshot(
    body: RecordSnapshotRequest, tenant_id: str = Depends(get_current_tenant_id), service: CapacityForecastService = Depends(get_capacity_forecast_service)
):
    return to_dict(await service.record_snapshot(tenant_id, **body.model_dump()))


@router.get("/{resource_type}/history")
async def history(
    resource_type: str, tenant_id: str = Depends(get_current_tenant_id), component_id: str | None = None,
    since: datetime | None = None, service: CapacityForecastService = Depends(get_capacity_forecast_service),
):
    return to_dict_list(await service.history(tenant_id, resource_type, component_id=component_id, since=since))


class ForecastRequest(BaseModel):
    component_id: str | None = None
    horizon_days: int | None = None
    capacity_limit: float | None = None


@router.post("/{resource_type}/forecast", status_code=201)
async def generate_forecast(
    resource_type: str, body: ForecastRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: CapacityForecastService = Depends(get_capacity_forecast_service),
):
    return to_dict(await service.generate_forecast(tenant_id, resource_type, **body.model_dump()))


@router.get("/{resource_type}/recommendation")
async def scaling_recommendation(
    resource_type: str, tenant_id: str = Depends(get_current_tenant_id), component_id: str | None = None,
    capacity_limit: float | None = None, service: CapacityForecastService = Depends(get_capacity_forecast_service),
):
    return await service.scaling_recommendation(tenant_id, resource_type, component_id=component_id, capacity_limit=capacity_limit)
