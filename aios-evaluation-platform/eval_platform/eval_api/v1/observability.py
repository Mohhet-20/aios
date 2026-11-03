"""Observability Platform: event ingestion from any upstream AIOS
platform, plus timeline/latency/failure/resource/token-cost queries."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.dependencies.dependencies import get_observability_ingestion_service, get_observability_monitoring_service
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.observability.ingestion_service import ObservabilityIngestionService
from eval_platform.observability.monitoring_service import ObservabilityMonitoringService

router = APIRouter(prefix="/observability", tags=["observability"])


class IngestEventRequest(BaseModel):
    workspace_id: str
    event_type: str
    source_platform: str
    status: str
    source_execution_id: str | None = None
    latency_ms: float | None = None
    queue_time_ms: float | None = None
    error_type: str | None = None
    retry_count: int = 0
    token_usage: dict | None = None
    cost: float | None = None
    resource_usage: dict | None = None
    payload: dict | None = None
    error_message: str | None = None


@router.post("/events", status_code=201)
async def ingest_event(body: IngestEventRequest, service: ObservabilityIngestionService = Depends(get_observability_ingestion_service)):
    event = await service.ingest_event(
        body.workspace_id, event_type=body.event_type, source_platform=body.source_platform, status=body.status,
        source_execution_id=body.source_execution_id, latency_ms=body.latency_ms, queue_time_ms=body.queue_time_ms,
        error_type=body.error_type, retry_count=body.retry_count, token_usage=body.token_usage, cost=body.cost,
        resource_usage=body.resource_usage, payload=body.payload, error_message=body.error_message,
    )
    return to_dict(event)


@router.get("/timeline")
async def get_timeline(workspace_id: str, source_execution_id: str, service: ObservabilityMonitoringService = Depends(get_observability_monitoring_service)):
    return to_dict_list(await service.get_timeline(workspace_id, source_execution_id))


@router.get("/stats/latency")
async def latency_stats(workspace_id: str, event_type: str | None = None, service: ObservabilityMonitoringService = Depends(get_observability_monitoring_service)):
    return await service.get_latency_stats(workspace_id, event_type=event_type)


@router.get("/stats/queue-time")
async def queue_time_stats(workspace_id: str, service: ObservabilityMonitoringService = Depends(get_observability_monitoring_service)):
    return await service.get_queue_time_stats(workspace_id)


@router.get("/stats/failures")
async def failure_stats(workspace_id: str, service: ObservabilityMonitoringService = Depends(get_observability_monitoring_service)):
    return await service.get_failure_stats(workspace_id)


@router.get("/stats/resource-usage")
async def resource_usage_stats(workspace_id: str, service: ObservabilityMonitoringService = Depends(get_observability_monitoring_service)):
    return await service.get_resource_usage_stats(workspace_id)


@router.get("/stats/tokens-and-cost")
async def token_and_cost_stats(workspace_id: str, service: ObservabilityMonitoringService = Depends(get_observability_monitoring_service)):
    return await service.get_token_and_cost_stats(workspace_id)
