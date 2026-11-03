"""Performance analysis API."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from observability_platform.analytics.performance_service import PerformanceAnalysisService
from observability_platform.dependencies.dependencies import get_current_tenant_id, get_performance_analysis_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/latency/{metric_name}")
async def latency_analysis(
    metric_name: str, tenant_id: str = Depends(get_current_tenant_id), component_id: str | None = None,
    start_time: datetime | None = None, end_time: datetime | None = None,
    service: PerformanceAnalysisService = Depends(get_performance_analysis_service),
):
    result = await service.latency_analysis(tenant_id, metric_name, component_id=component_id, start_time=start_time, end_time=end_time)
    return result.__dict__


@router.get("/bottleneck/{trace_id}")
async def bottleneck(trace_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PerformanceAnalysisService = Depends(get_performance_analysis_service)):
    return await service.detect_bottleneck(tenant_id, trace_id)


@router.get("/slow-queries")
async def slow_queries(tenant_id: str = Depends(get_current_tenant_id), threshold_ms: float = 100.0, service: PerformanceAnalysisService = Depends(get_performance_analysis_service)):
    return await service.slow_query_analysis(tenant_id, threshold_ms=threshold_ms)


@router.get("/performance/{span_kind}")
async def performance_by_kind(span_kind: str, tenant_id: str = Depends(get_current_tenant_id), service: PerformanceAnalysisService = Depends(get_performance_analysis_service)):
    return await service.performance_by_span_kind(tenant_id, span_kind)


@router.get("/cache")
async def cache_analysis(tenant_id: str = Depends(get_current_tenant_id), metric_name: str = "cache_hit_ratio", service: PerformanceAnalysisService = Depends(get_performance_analysis_service)):
    result = await service.cache_analysis(tenant_id, metric_name=metric_name)
    return result.__dict__
