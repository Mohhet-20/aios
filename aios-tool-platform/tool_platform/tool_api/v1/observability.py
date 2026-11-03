"""Observability: execution timeline/logs/resource usage + per-tool
rollups (success rate, latency, failures, retries, resource usage
stats, usage trends) + per-workspace call volume — the "Execution Logs"
and "Monitoring Dashboard" frontend surfaces."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from tool_platform.dependencies.dependencies import get_observability_service
from tool_platform.monitoring.observability_service import ObservabilityService

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/executions/{execution_id}/timeline")
async def get_execution_timeline(execution_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_execution_timeline(execution_id)


@router.get("/executions/{execution_id}/logs")
async def list_execution_logs(execution_id: str, level: str | None = None, svc: ObservabilityService = Depends(get_observability_service)):
    from tool_platform.tool_api.serialization import to_dict_list

    return to_dict_list(await svc.list_execution_logs(execution_id, level=level))


@router.get("/executions/{execution_id}/queue-time")
async def get_queue_time(execution_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return {"queue_time_ms": await svc.get_queue_time_ms(execution_id)}


@router.get("/executions/{execution_id}/resource-usage")
async def get_resource_usage(execution_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_resource_usage(execution_id)


@router.get("/tools/{tool_id}/success-rate")
async def get_success_rate(tool_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_success_rate(tool_id)


@router.get("/tools/{tool_id}/latency")
async def get_latency_stats(tool_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_latency_stats(tool_id)


@router.get("/tools/{tool_id}/failures")
async def get_failure_stats(tool_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_failure_stats(tool_id)


@router.get("/tools/{tool_id}/retries")
async def get_retry_stats(tool_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_retry_stats(tool_id)


@router.get("/tools/{tool_id}/resource-usage-stats")
async def get_resource_usage_stats(tool_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_resource_usage_stats(tool_id)


@router.get("/tools/{tool_id}/usage-trends")
async def get_usage_trends(tool_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_usage_trends(tool_id)


@router.get("/workspaces/{workspace_id}/call-volume")
async def get_workspace_call_volume(workspace_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.get_workspace_call_volume(workspace_id)
