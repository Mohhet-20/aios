"""Data Warehouse & Metrics Registry: metric definitions and raw event
ingestion."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_event_ingestion_service,
    get_metric_registry_service,
)
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

router = APIRouter(prefix="/metrics", tags=["warehouse"])
events_router = APIRouter(prefix="/metric-events", tags=["warehouse"])


class RegisterMetricRequest(BaseModel):
    key: str
    name: str
    data_source: str
    unit: str = "count"
    aggregation_type: str = "sum"
    description: str | None = None
    tags: list[str] | None = None


@router.post("", status_code=201)
async def register_metric(
    body: RegisterMetricRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: MetricRegistryService = Depends(get_metric_registry_service),
):
    return to_dict(await service.register_metric(tenant_id, **body.model_dump()))


@router.get("")
async def list_metrics(
    data_source: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: MetricRegistryService = Depends(get_metric_registry_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, data_source=data_source))


@router.get("/{key}")
async def get_metric(
    key: str, tenant_id: str = Depends(get_current_tenant_id), service: MetricRegistryService = Depends(get_metric_registry_service),
):
    return to_dict(await service.get_by_key(tenant_id, key))


class IngestEventRequest(BaseModel):
    metric_key: str
    data_source: str
    value: float
    dimensions: dict | None = None
    occurred_at: datetime | None = None


@events_router.post("", status_code=201)
async def ingest_event(
    body: IngestEventRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: EventIngestionService = Depends(get_event_ingestion_service),
):
    return to_dict(await service.ingest_event(tenant_id, **body.model_dump()))


class IngestBatchRequest(BaseModel):
    events: list[dict]


@events_router.post("/batch", status_code=201)
async def ingest_batch(
    body: IngestBatchRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: EventIngestionService = Depends(get_event_ingestion_service),
):
    return to_dict_list(await service.ingest_batch(tenant_id, body.events))


@events_router.get("")
async def list_metric_events(
    metric_key: str, tenant_id: str = Depends(get_current_tenant_id),
    service: EventIngestionService = Depends(get_event_ingestion_service),
):
    return to_dict_list(await service.list_for_metric(tenant_id, metric_key))
