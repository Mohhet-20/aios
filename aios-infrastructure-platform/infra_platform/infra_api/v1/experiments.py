"""Experiment Tracking API: experiments, runs, metrics, parameters,
and run comparison."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import get_current_tenant_id, get_experiment_run_service, get_experiment_service
from infra_platform.experiments.experiment_service import ExperimentRunService, ExperimentService
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/experiments", tags=["experiments"])


class CreateExperimentRequest(BaseModel):
    name: str
    description: str | None = None


@router.post("", status_code=201)
async def create_experiment(body: CreateExperimentRequest, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentService = Depends(get_experiment_service)):
    return to_dict(await service.create_experiment(tenant_id, **body.model_dump()))


@router.get("")
async def list_experiments(tenant_id: str = Depends(get_current_tenant_id), service: ExperimentService = Depends(get_experiment_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


class StartRunRequest(BaseModel):
    run_name: str | None = None
    source: str | None = None


@router.post("/{experiment_id}/runs", status_code=201)
async def start_run(experiment_id: str, body: StartRunRequest, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict(await service.start_run(tenant_id, experiment_id, **body.model_dump()))


@router.get("/{experiment_id}/runs")
async def list_runs(experiment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict_list(await service.list_for_experiment(tenant_id, experiment_id))


@router.post("/runs/{run_id}/complete")
async def complete_run(run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict(await service.complete_run(tenant_id, run_id))


@router.post("/runs/{run_id}/fail")
async def fail_run(run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict(await service.fail_run(tenant_id, run_id))


@router.post("/runs/{run_id}/kill")
async def kill_run(run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict(await service.kill_run(tenant_id, run_id))


class LogMetricRequest(BaseModel):
    key: str
    value: float
    step: int = 0


@router.post("/runs/{run_id}/metrics", status_code=201)
async def log_metric(run_id: str, body: LogMetricRequest, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict(await service.log_metric(tenant_id, run_id, **body.model_dump()))


@router.get("/runs/{run_id}/metrics")
async def get_metrics(run_id: str, key: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict_list(await service.get_metrics(tenant_id, run_id, key=key))


class LogParamRequest(BaseModel):
    key: str
    value: str


@router.post("/runs/{run_id}/params", status_code=201)
async def log_param(run_id: str, body: LogParamRequest, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict(await service.log_param(tenant_id, run_id, **body.model_dump()))


@router.get("/runs/{run_id}/params")
async def get_params(run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)):
    return to_dict_list(await service.get_params(tenant_id, run_id))


@router.get("/compare")
async def compare_runs(
    run_ids: str, metric_key: str, tenant_id: str = Depends(get_current_tenant_id), service: ExperimentRunService = Depends(get_experiment_run_service)
):
    return await service.compare_runs(tenant_id, run_ids.split(","), metric_key=metric_key)
