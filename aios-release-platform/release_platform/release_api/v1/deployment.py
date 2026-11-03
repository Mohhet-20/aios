"""Deployment Orchestration: create and drive deployments through
their queued -> in_progress -> succeeded/failed -> rolled_back
lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_deployment_service
from release_platform.deployment.deployment_service import DeploymentService
from release_platform.release_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/deployments", tags=["deployment"])


class CreateDeploymentRequest(BaseModel):
    release_id: str
    environment_id: str
    target_type: str
    initiated_by: str | None = None


@router.post("", status_code=201)
async def create_deployment(
    body: CreateDeploymentRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service),
):
    return to_dict(await service.create_deployment(tenant_id, **body.model_dump()))


@router.get("")
async def list_deployments(
    environment_id: str | None = None, status: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service),
):
    return to_dict_list(await service.list_deployments(tenant_id, environment_id=environment_id, status=status))


@router.get("/{deployment_id}")
async def get_deployment(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service),
):
    return to_dict(await service.get_or_404(tenant_id, deployment_id))


@router.post("/{deployment_id}/start")
async def start_deployment(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service),
):
    return to_dict(await service.start(tenant_id, deployment_id))


@router.post("/{deployment_id}/succeed")
async def succeed_deployment(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service),
):
    return to_dict(await service.succeed(tenant_id, deployment_id))


class FailDeploymentRequest(BaseModel):
    reason: str


@router.post("/{deployment_id}/fail")
async def fail_deployment(
    deployment_id: str, body: FailDeploymentRequest,
    tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service),
):
    return to_dict(await service.fail(tenant_id, deployment_id, reason=body.reason))


@router.post("/{deployment_id}/mark-rolled-back")
async def mark_rolled_back(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentService = Depends(get_deployment_service),
):
    return to_dict(await service.mark_rolled_back(tenant_id, deployment_id))
