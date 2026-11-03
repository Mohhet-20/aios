"""Benchmark CRUD + comparison-run execution (model benchmarking,
prompt A/B/multivariate testing, agent/workflow comparison) — the
multi-candidate generalization of an evaluation run, over the same
`ReferenceTargetExecutor` seam."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.benchmarking.benchmark_service import BenchmarkService
from eval_platform.benchmarking.run_service import BenchmarkRunService
from eval_platform.core.pagination import PaginationParams
from eval_platform.dependencies.dependencies import get_benchmark_run_service, get_benchmark_service
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.execution.executor import ReferenceTargetExecutor

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])
_executor = ReferenceTargetExecutor()


class CreateBenchmarkRequest(BaseModel):
    workspace_id: str
    organization_id: str
    name: str
    owner_id: str
    benchmark_type: str
    mode: str
    dataset_id: str | None = None
    slug: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    metric_keys: list[str] | None = None


class UpdateBenchmarkRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    dataset_id: str | None = None
    metric_keys: list[str] | None = None


class StartBenchmarkRunRequest(BaseModel):
    candidates: list[dict]
    triggered_by: str | None = None


@router.post("", status_code=201)
async def create_benchmark(body: CreateBenchmarkRequest, service: BenchmarkService = Depends(get_benchmark_service)):
    benchmark = await service.create_benchmark(
        body.workspace_id, name=body.name, owner_id=body.owner_id, benchmark_type=body.benchmark_type, mode=body.mode,
        organization_id=body.organization_id, dataset_id=body.dataset_id, slug=body.slug, description=body.description,
        tags=body.tags, metric_keys=body.metric_keys,
    )
    return to_dict(benchmark)


@router.get("/{benchmark_id}")
async def get_benchmark(benchmark_id: str, service: BenchmarkService = Depends(get_benchmark_service)):
    return to_dict(await service.get_benchmark(benchmark_id))


@router.get("")
async def list_benchmarks(
    workspace_id: str, page: int = 1, page_size: int = 50, benchmark_type: str | None = None,
    service: BenchmarkService = Depends(get_benchmark_service),
):
    result = await service.list_benchmarks(workspace_id, PaginationParams(page=page, page_size=page_size), benchmark_type=benchmark_type)
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size}


@router.patch("/{benchmark_id}")
async def update_benchmark(benchmark_id: str, body: UpdateBenchmarkRequest, service: BenchmarkService = Depends(get_benchmark_service)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    return to_dict(await service.update_benchmark(benchmark_id, **fields))


@router.delete("/{benchmark_id}", status_code=204)
async def delete_benchmark(benchmark_id: str, service: BenchmarkService = Depends(get_benchmark_service)):
    await service.delete_benchmark(benchmark_id)


# -- runs --------------------------------------------------------------------------------

@router.post("/{benchmark_id}/runs", status_code=201)
async def start_benchmark_run(benchmark_id: str, body: StartBenchmarkRunRequest, service: BenchmarkRunService = Depends(get_benchmark_run_service)):
    return to_dict(await service.start_run(benchmark_id, body.candidates, triggered_by=body.triggered_by))


@router.post("/runs/{run_id}/execute")
async def execute_benchmark_run(run_id: str, service: BenchmarkRunService = Depends(get_benchmark_run_service)):
    return to_dict(await service.execute_run(run_id, _executor))


@router.get("/runs/{run_id}")
async def get_benchmark_run(run_id: str, service: BenchmarkRunService = Depends(get_benchmark_run_service)):
    return to_dict(await service.get_run(run_id))


@router.get("/{benchmark_id}/runs")
async def list_benchmark_runs(benchmark_id: str, service: BenchmarkRunService = Depends(get_benchmark_run_service)):
    return to_dict_list(await service.list_runs(benchmark_id))


@router.get("/runs/{run_id}/results")
async def list_candidate_results(run_id: str, service: BenchmarkRunService = Depends(get_benchmark_run_service)):
    return to_dict_list(await service.list_candidate_results(run_id))


@router.get("/runs/{run_id}/leaderboard")
async def leaderboard(run_id: str, service: BenchmarkRunService = Depends(get_benchmark_run_service)):
    return to_dict_list(await service.leaderboard(run_id))
