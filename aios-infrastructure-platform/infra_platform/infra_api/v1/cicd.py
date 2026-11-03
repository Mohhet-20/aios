"""CI/CD Platform API: pipeline definitions, triggered runs with
per-stage tracking, deployment gates, and releases."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.cicd.cicd_service import DeploymentGateService, PipelineRunService, PipelineService, ReleaseService
from infra_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_deployment_gate_service,
    get_pipeline_run_service,
    get_pipeline_service,
    get_release_service,
)
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/cicd", tags=["cicd"])


class CreatePipelineRequest(BaseModel):
    name: str
    repository: str
    default_branch: str = "main"
    stages: list[str] | None = None


@router.post("/pipelines", status_code=201)
async def create_pipeline(body: CreatePipelineRequest, tenant_id: str = Depends(get_current_tenant_id), service: PipelineService = Depends(get_pipeline_service)):
    return to_dict(await service.create_pipeline(tenant_id, **body.model_dump()))


@router.get("/pipelines")
async def list_pipelines(tenant_id: str = Depends(get_current_tenant_id), service: PipelineService = Depends(get_pipeline_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


class SetEnabledRequest(BaseModel):
    enabled: bool


@router.patch("/pipelines/{pipeline_id}/enabled")
async def set_pipeline_enabled(pipeline_id: str, body: SetEnabledRequest, tenant_id: str = Depends(get_current_tenant_id), service: PipelineService = Depends(get_pipeline_service)):
    return to_dict(await service.set_enabled(tenant_id, pipeline_id, **body.model_dump()))


class TriggerRunRequest(BaseModel):
    commit_sha: str
    branch: str | None = None
    triggered_by: str | None = None


@router.post("/pipelines/{pipeline_id}/runs", status_code=201)
async def trigger_run(pipeline_id: str, body: TriggerRunRequest, tenant_id: str = Depends(get_current_tenant_id), service: PipelineRunService = Depends(get_pipeline_run_service)):
    return to_dict(await service.trigger_run(tenant_id, pipeline_id, **body.model_dump()))


@router.get("/pipelines/{pipeline_id}/runs")
async def list_runs(pipeline_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PipelineRunService = Depends(get_pipeline_run_service)):
    return to_dict_list(await service.list_runs_for_pipeline(tenant_id, pipeline_id))


@router.post("/runs/{run_id}/start")
async def start_run(run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PipelineRunService = Depends(get_pipeline_run_service)):
    return to_dict(await service.start_run(tenant_id, run_id))


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PipelineRunService = Depends(get_pipeline_run_service)):
    return to_dict(await service.cancel_run(tenant_id, run_id))


@router.get("/runs/{run_id}/stages")
async def list_stages(run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PipelineRunService = Depends(get_pipeline_run_service)):
    return to_dict_list(await service.list_stages(tenant_id, run_id))


@router.post("/runs/{run_id}/stages/{stage_type}/start")
async def start_stage(run_id: str, stage_type: str, tenant_id: str = Depends(get_current_tenant_id), service: PipelineRunService = Depends(get_pipeline_run_service)):
    return to_dict(await service.start_stage(tenant_id, run_id, stage_type))


class CompleteStageRequest(BaseModel):
    success: bool
    logs_excerpt: str = ""


@router.post("/runs/{run_id}/stages/{stage_type}/complete")
async def complete_stage(
    run_id: str, stage_type: str, body: CompleteStageRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PipelineRunService = Depends(get_pipeline_run_service),
):
    return to_dict(await service.complete_stage(tenant_id, run_id, stage_type, **body.model_dump()))


class CreateGateRequest(BaseModel):
    name: str
    required_approvals: int | None = None


@router.post("/runs/{pipeline_run_id}/gates", status_code=201)
async def create_gate(
    pipeline_run_id: str, body: CreateGateRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentGateService = Depends(get_deployment_gate_service)
):
    return to_dict(await service.create_gate(tenant_id, pipeline_run_id, **body.model_dump()))


@router.post("/gates/{gate_id}/approve")
async def approve_gate(gate_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentGateService = Depends(get_deployment_gate_service)):
    return to_dict(await service.approve(tenant_id, gate_id))


@router.post("/gates/{gate_id}/reject")
async def reject_gate(gate_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentGateService = Depends(get_deployment_gate_service)):
    return to_dict(await service.reject(tenant_id, gate_id))


@router.post("/gates/{gate_id}/bypass")
async def bypass_gate(gate_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentGateService = Depends(get_deployment_gate_service)):
    return to_dict(await service.bypass(tenant_id, gate_id))


class CreateReleaseRequest(BaseModel):
    name: str
    version: str
    pipeline_run_id: str | None = None


@router.post("/releases", status_code=201)
async def create_release(body: CreateReleaseRequest, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service)):
    return to_dict(await service.create_release(tenant_id, **body.model_dump()))


@router.get("/releases")
async def list_releases(tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/releases/{release_id}/submit")
async def submit_release(release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service)):
    return to_dict(await service.submit_for_approval(tenant_id, release_id))


@router.post("/releases/{release_id}/approve")
async def approve_release(release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service)):
    return to_dict(await service.approve(tenant_id, release_id))


@router.post("/releases/{release_id}/publish")
async def publish_release(release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service)):
    return to_dict(await service.publish(tenant_id, release_id))


@router.post("/releases/{release_id}/rollback")
async def rollback_release(release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service)):
    return to_dict(await service.rollback(tenant_id, release_id))
