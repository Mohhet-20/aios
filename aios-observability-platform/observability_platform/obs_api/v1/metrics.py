"""Metrics platform API: ingestion and querying."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_metric_ingest_service,
    get_metric_query_service,
)
from observability_platform.metrics.ingest_service import MetricIngestService
from observability_platform.metrics.query_service import MetricQueryService
from observability_platform.obs_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/metrics", tags=["metrics"])


class IngestMetricRequest(BaseModel):
    name: str
    metric_type: str
    value: float
    unit: str | None = None
    labels: dict | None = None
    component_id: str | None = None
    service_name: str | None = None


@router.post("", status_code=201)
async def ingest_metric(
    body: IngestMetricRequest, tenant_id: str = Depends(get_current_tenant_id), service: MetricIngestService = Depends(get_metric_ingest_service)
):
    return to_dict(await service.ingest(tenant_id, **body.model_dump()))


class IngestMetricBatchRequest(BaseModel):
    points: list[IngestMetricRequest]


@router.post("/batch", status_code=201)
async def ingest_metric_batch(
    body: IngestMetricBatchRequest, tenant_id: str = Depends(get_current_tenant_id), service: MetricIngestService = Depends(get_metric_ingest_service)
):
    return to_dict_list(await service.ingest_batch(tenant_id, [p.model_dump() for p in body.points]))


@router.get("/{metric_name}/range")
async def query_range(
    metric_name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    component_id: str | None = None,
    service: MetricQueryService = Depends(get_metric_query_service),
):
    return to_dict_list(await service.query_range(tenant_id, metric_name, start_time=start_time, end_time=end_time, component_id=component_id))


@router.get("/{metric_name}/latest")
async def latest(
    metric_name: str, tenant_id: str = Depends(get_current_tenant_id), component_id: str | None = None,
    service: MetricQueryService = Depends(get_metric_query_service),
):
    return to_dict(await service.latest(tenant_id, metric_name, component_id=component_id))


@router.get("/{metric_name}/aggregate")
async def aggregate_range(
    metric_name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    component_id: str | None = None,
    service: MetricQueryService = Depends(get_metric_query_service),
):
    result = await service.aggregate_range(tenant_id, metric_name, start_time=start_time, end_time=end_time, component_id=component_id)
    return result.__dict__


@router.get("/{metric_name}/timeseries")
async def time_series(
    metric_name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    component_id: str | None = None,
    bucket_seconds: int | None = None,
    service: MetricQueryService = Depends(get_metric_query_service),
):
    return await service.time_series(
        tenant_id, metric_name, start_time=start_time, end_time=end_time, component_id=component_id, bucket_seconds=bucket_seconds
    )
