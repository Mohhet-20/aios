"""Performance Testing Engine: run lifecycle plus benchmark result
recording across the six performance test types."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import (
    get_benchmark_result_service,
    get_current_tenant_id,
    get_performance_test_run_service,
)
from quality_platform.performance.benchmark_result_service import BenchmarkResultService
from quality_platform.performance.performance_test_run_service import PerformanceTestRunService
from quality_platform.qa_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/performance-runs", tags=["performance"])


class RequestRunRequest(BaseModel):
    performance_test_type: str
    target_ref: str
    config: dict | None = None


@router.post("", status_code=201)
async def request_run(
    body: RequestRunRequest, tenant_id: str = Depends(get_current_tenant_id), service: PerformanceTestRunService = Depends(get_performance_test_run_service),
):
    return to_dict(await service.request_run(tenant_id, performance_test_type=body.performance_test_type, target_ref=body.target_ref, config=body.config))


@router.get("/{run_id}")
async def get_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PerformanceTestRunService = Depends(get_performance_test_run_service),
):
    return to_dict(await service.get_or_404(tenant_id, run_id))


@router.post("/{run_id}/start")
async def start_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PerformanceTestRunService = Depends(get_performance_test_run_service),
):
    return to_dict(await service.start(tenant_id, run_id))


class RecordBenchmarkRequest(BaseModel):
    metric_type: str
    value: float
    unit: str = "ms"


@router.post("/{run_id}/benchmarks", status_code=201)
async def record_benchmark(
    run_id: str, body: RecordBenchmarkRequest, tenant_id: str = Depends(get_current_tenant_id), service: BenchmarkResultService = Depends(get_benchmark_result_service),
):
    return to_dict(await service.record_result(tenant_id, run_id, metric_type=body.metric_type, value=body.value, unit=body.unit))


@router.get("/{run_id}/benchmarks")
async def list_benchmarks(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BenchmarkResultService = Depends(get_benchmark_result_service),
):
    return to_dict_list(await service.list_for_run(tenant_id, run_id))


@router.post("/{run_id}/finish")
async def finish_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PerformanceTestRunService = Depends(get_performance_test_run_service),
):
    return to_dict(await service.finish_run(tenant_id, run_id))


@router.get("")
async def list_runs(
    performance_test_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: PerformanceTestRunService = Depends(get_performance_test_run_service),
):
    return to_dict_list(await service.list_runs(tenant_id, performance_test_type=performance_test_type))
