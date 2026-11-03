"""Observability & Benchmarking: latency/throughput recording +
percentile/SLO reads, and the benchmark-run lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from perf_platform.dependencies.dependencies import (
    get_benchmark_service,
    get_current_tenant_id,
    get_latency_service,
    get_throughput_service,
)
from perf_platform.observability.observability_service import (
    BenchmarkService,
    LatencyTrackingService,
    ThroughputTrackingService,
)
from perf_platform.perf_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/observability", tags=["observability"])
benchmarks_router = APIRouter(prefix="/benchmarks", tags=["observability"])


class RecordLatencyRequest(BaseModel):
    operation: str
    duration_ms: float


@router.post("/latency")
async def record_latency(
    body: RecordLatencyRequest, tenant_id: str = Depends(get_current_tenant_id), service: LatencyTrackingService = Depends(get_latency_service),
):
    return to_dict(await service.record(tenant_id, body.operation, body.duration_ms))


@router.get("/latency/{operation}/percentiles")
async def latency_percentiles(
    operation: str, tenant_id: str = Depends(get_current_tenant_id), service: LatencyTrackingService = Depends(get_latency_service),
):
    return await service.percentiles(tenant_id, operation)


@router.get("/latency/{operation}/slo")
async def latency_slo(
    operation: str, tenant_id: str = Depends(get_current_tenant_id), service: LatencyTrackingService = Depends(get_latency_service),
):
    return await service.slo_status(tenant_id, operation)


class RecordThroughputRequest(BaseModel):
    operation: str
    request_count: int
    window_seconds: float


@router.post("/throughput")
async def record_throughput(
    body: RecordThroughputRequest, tenant_id: str = Depends(get_current_tenant_id), service: ThroughputTrackingService = Depends(get_throughput_service),
):
    return to_dict(await service.record(tenant_id, body.operation, request_count=body.request_count, window_seconds=body.window_seconds))


@router.get("/throughput/{operation}/rate")
async def throughput_rate(
    operation: str, tenant_id: str = Depends(get_current_tenant_id), service: ThroughputTrackingService = Depends(get_throughput_service),
):
    return {"operation": operation, "requests_per_second": await service.current_rate(tenant_id, operation)}


class StartBenchmarkRequest(BaseModel):
    name: str
    target_ref: str | None = None


@benchmarks_router.post("", status_code=201)
async def start_benchmark(
    body: StartBenchmarkRequest, tenant_id: str = Depends(get_current_tenant_id), service: BenchmarkService = Depends(get_benchmark_service),
):
    return to_dict(await service.start(tenant_id, name=body.name, target_ref=body.target_ref))


class CompleteBenchmarkRequest(BaseModel):
    baseline_ms: float
    optimized_ms: float


@benchmarks_router.post("/{run_id}/complete")
async def complete_benchmark(
    run_id: str, body: CompleteBenchmarkRequest, tenant_id: str = Depends(get_current_tenant_id), service: BenchmarkService = Depends(get_benchmark_service),
):
    return to_dict(await service.complete(tenant_id, run_id, baseline_ms=body.baseline_ms, optimized_ms=body.optimized_ms))


@benchmarks_router.post("/{run_id}/fail")
async def fail_benchmark(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BenchmarkService = Depends(get_benchmark_service),
):
    return to_dict(await service.fail(tenant_id, run_id))


@benchmarks_router.get("")
async def list_benchmarks(
    status: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: BenchmarkService = Depends(get_benchmark_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, status=status))
