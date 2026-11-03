"""Observability surface: execution timeline/graph, logs, and workflow-level
aggregate metrics (success rate, latency, node durations, failures,
retries, token usage). Reports only genuinely logged data — no fabricated
CPU/memory/cost figures (see module docstring on ObservabilityService)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from workflow_platform.monitoring.observability_service import ObservabilityService
from workflow_platform.workflow_api.dependencies import get_observability_service
from workflow_platform.workflow_api.serialization import to_dict_list

router = APIRouter(tags=["observability"])


@router.get("/executions/{execution_id}/timeline")
async def get_execution_timeline(execution_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_execution_timeline(execution_id)


@router.get("/executions/{execution_id}/graph")
async def get_execution_graph(execution_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_execution_graph(execution_id)


@router.get("/executions/{execution_id}/logs")
async def list_execution_logs(execution_id: str, level: str | None = None, svc: ObservabilityService = Depends(get_observability_service)):
    return to_dict_list(await svc.list_execution_logs(execution_id, level=level))


@router.get("/executions/{execution_id}/queue-time-ms")
async def get_queue_time_ms(execution_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return {"queue_time_ms": await svc.get_queue_time_ms(execution_id)}


@router.get("/workflows/{workflow_id}/metrics/success-rate")
async def get_success_rate(workflow_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_success_rate(workflow_id)


@router.get("/workflows/{workflow_id}/metrics/latency")
async def get_latency_stats(workflow_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_latency_stats(workflow_id)


@router.get("/workflows/{workflow_id}/metrics/node-durations")
async def get_node_duration_stats(workflow_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_node_duration_stats(workflow_id)


@router.get("/workflows/{workflow_id}/metrics/failures")
async def get_failure_stats(workflow_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_failure_stats(workflow_id)


@router.get("/workflows/{workflow_id}/metrics/retries")
async def get_retry_stats(workflow_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_retry_stats(workflow_id)


@router.get("/workflows/{workflow_id}/metrics/token-usage")
async def get_token_usage(workflow_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_token_usage(workflow_id)
