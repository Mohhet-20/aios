"""Deployment Strategies API: rolling/blue-green/canary/shadow/
recreate deployment lifecycle, canary steps, blue-green cutover,
auto-rollback on error rate, and feature flags."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import get_current_tenant_id, get_deployment_service, get_feature_flag_service
from infra_platform.deployment.deployment_service import DeploymentService, FeatureFlagService
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/deployments", tags=["deployment"])


class CreateDeploymentRequest(BaseModel):
    name: str
    target_version: str
    service_id: str | None = None
    strategy: str = "rolling"
    previous_version: str | None = None


@router.post("", status_code=201)
async def create_deployment(body: CreateDeploymentRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.create_deployment(tenant_id, **body.model_dump()))


@router.post("/{deployment_id}/start")
async def start(deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.start(tenant_id, deployment_id))


@router.post("/{deployment_id}/pause")
async def pause(deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.pause(tenant_id, deployment_id))


@router.post("/{deployment_id}/resume")
async def resume(deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.resume(tenant_id, deployment_id))


@router.post("/{deployment_id}/succeed")
async def succeed(deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.succeed(tenant_id, deployment_id))


class FailRequest(BaseModel):
    reason: str = ""


@router.post("/{deployment_id}/fail")
async def fail(deployment_id: str, body: FailRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.fail(tenant_id, deployment_id, **body.model_dump()))


class RollbackRequest(BaseModel):
    reason: str = ""


@router.post("/{deployment_id}/rollback")
async def rollback(deployment_id: str, body: RollbackRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.rollback(tenant_id, deployment_id, **body.model_dump()))


class CanaryStepRequest(BaseModel):
    step_percentage: int


@router.post("/{deployment_id}/canary/advance")
async def advance_canary_step(deployment_id: str, body: CanaryStepRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.advance_canary_step(tenant_id, deployment_id, **body.model_dump()))


@router.post("/{deployment_id}/blue-green/cutover")
async def blue_green_cutover(deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await service.blue_green_cutover(tenant_id, deployment_id))


@router.get("/{deployment_id}/events")
async def list_events(deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict_list(await service.list_events(tenant_id, deployment_id))


@router.get("/{deployment_id}/traffic-splits")
async def list_traffic_splits(deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return to_dict_list(await service.list_traffic_splits(tenant_id, deployment_id))


@router.get("/status-counts")
async def count_by_status(tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service)):
    return await service.count_by_status(tenant_id)


class CreateFlagRequest(BaseModel):
    key: str
    description: str | None = None
    is_enabled: bool = False
    rollout_percentage: int = 0


@router.post("/feature-flags", status_code=201)
async def create_flag(body: CreateFlagRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service)):
    return to_dict(await service.create_flag(tenant_id, **body.model_dump()))


@router.get("/feature-flags")
async def list_flags(tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/feature-flags/{key}/enable")
async def enable_flag(key: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service)):
    return to_dict(await service.enable(tenant_id, key))


@router.post("/feature-flags/{key}/disable")
async def disable_flag(key: str, tenant_id: str = Depends(get_current_tenant_id), service: FeatureFlagService = Depends(get_feature_flag_service)):
    return to_dict(await service.disable(tenant_id, key))
