"""Observability: platform usage events, query performance, forecast
accuracy, and recommendation-outcome analytics."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_forecast_accuracy_service,
    get_query_performance_service,
    get_recommendation_analytics_service,
    get_usage_event_service,
)
from analytics_platform.observability.forecast_accuracy_service import ForecastAccuracyService
from analytics_platform.observability.query_performance_service import QueryPerformanceService
from analytics_platform.observability.recommendation_analytics_service import RecommendationAnalyticsService
from analytics_platform.observability.usage_service import UsageEventService

router = APIRouter(prefix="/usage-events", tags=["observability"])
query_perf_router = APIRouter(prefix="/query-performance", tags=["observability"])
accuracy_router = APIRouter(prefix="/forecast-accuracy", tags=["observability"])
recommendation_analytics_router = APIRouter(prefix="/recommendation-analytics", tags=["observability"])


class RecordUsageEventRequest(BaseModel):
    event_type: str
    resource_type: str | None = None
    resource_id: str | None = None
    actor_id: str | None = None
    duration_ms: float = 0.0


@router.post("", status_code=201)
async def record_usage_event(
    body: RecordUsageEventRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: UsageEventService = Depends(get_usage_event_service),
):
    return to_dict(await service.record(tenant_id, **body.model_dump()))


@router.get("")
async def list_usage_events(
    event_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: UsageEventService = Depends(get_usage_event_service),
):
    return to_dict_list(await service.list_recent(tenant_id, event_type=event_type))


@router.get("/summary")
async def summarize_usage(
    tenant_id: str = Depends(get_current_tenant_id), service: UsageEventService = Depends(get_usage_event_service),
):
    return await service.summarize(tenant_id)


class RecordQueryPerformanceRequest(BaseModel):
    query_ref: str
    duration_ms: float
    row_count: int = 0


@query_perf_router.post("", status_code=201)
async def record_query_performance(
    body: RecordQueryPerformanceRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: QueryPerformanceService = Depends(get_query_performance_service),
):
    return to_dict(await service.record(tenant_id, **body.model_dump()))


@query_perf_router.get("/slow")
async def list_slow_queries(
    threshold_ms: float, tenant_id: str = Depends(get_current_tenant_id),
    service: QueryPerformanceService = Depends(get_query_performance_service),
):
    return to_dict_list(await service.list_slow_queries(tenant_id, threshold_ms=threshold_ms))


class RecordForecastAccuracyRequest(BaseModel):
    forecast_job_id: str
    predicted_value: float
    actual_value: float


@accuracy_router.post("", status_code=201)
async def record_forecast_accuracy(
    body: RecordForecastAccuracyRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ForecastAccuracyService = Depends(get_forecast_accuracy_service),
):
    return to_dict(await service.record_accuracy(tenant_id, **body.model_dump()))


@accuracy_router.get("/{forecast_job_id}")
async def list_forecast_accuracy(
    forecast_job_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ForecastAccuracyService = Depends(get_forecast_accuracy_service),
):
    return to_dict_list(await service.list_for_job(tenant_id, forecast_job_id))


@accuracy_router.get("/{forecast_job_id}/average-error")
async def average_forecast_error(
    forecast_job_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ForecastAccuracyService = Depends(get_forecast_accuracy_service),
):
    return {"average_error_pct": await service.average_error(tenant_id, forecast_job_id)}


@recommendation_analytics_router.get("/acceptance-rate")
async def acceptance_rate(
    tenant_id: str = Depends(get_current_tenant_id), service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
):
    return {"acceptance_rate": await service.acceptance_rate(tenant_id)}


@recommendation_analytics_router.get("/outcome-breakdown")
async def outcome_breakdown(
    tenant_id: str = Depends(get_current_tenant_id), service: RecommendationAnalyticsService = Depends(get_recommendation_analytics_service),
):
    return await service.outcome_breakdown(tenant_id)
