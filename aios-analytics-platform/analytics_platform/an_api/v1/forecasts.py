"""Forecasting Engine: forecast job requests and execution."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dependencies.dependencies import get_current_tenant_id, get_forecast_job_service
from analytics_platform.forecasting.forecast_job_service import ForecastJobService

router = APIRouter(prefix="/forecasts", tags=["forecasting"])


class RequestForecastRequest(BaseModel):
    forecast_type: str
    metric_key: str
    method: str = "linear_regression"
    horizon_days: int = 30


@router.post("", status_code=201)
async def request_forecast(
    body: RequestForecastRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ForecastJobService = Depends(get_forecast_job_service),
):
    return to_dict(await service.request_job(tenant_id, **body.model_dump()))


@router.get("")
async def list_forecasts(
    forecast_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: ForecastJobService = Depends(get_forecast_job_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, forecast_type=forecast_type))


@router.get("/{job_id}")
async def get_forecast(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ForecastJobService = Depends(get_forecast_job_service),
):
    return to_dict(await service.get_or_404(tenant_id, job_id))


@router.post("/{job_id}/run")
async def run_forecast(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ForecastJobService = Depends(get_forecast_job_service),
):
    return to_dict(await service.run(tenant_id, job_id))
