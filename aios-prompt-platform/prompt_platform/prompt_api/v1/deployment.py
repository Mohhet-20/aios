"""Prompt Deployment: environments, approval-gated promotion, canary
rollout, rollback, deployment history, environment config."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.domain.enums import DeploymentEnvironment
from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_deployment_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_deployment.deployment_service import DeploymentService

router = APIRouter(prefix="/deployments", tags=["deployment"])


class RequestDeploymentRequest(BaseModel):
    prompt_id: str
    version_id: str
    environment: DeploymentEnvironment
    canary_percent: float = 100.0
    notes: str | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


class PromoteCanaryRequest(BaseModel):
    canary_percent: float = 100.0


class RollbackRequest(BaseModel):
    target_version_id: str | None = None
    reason: str | None = None


class EnvConfigRequest(BaseModel):
    workspace_id: str
    variables: dict


@router.post("", status_code=201)
async def request_deployment(body: RequestDeploymentRequest, actor_id: str = Depends(get_current_actor_id), svc: DeploymentService = Depends(get_deployment_service)):
    deployment = await svc.request_deployment(
        body.prompt_id, body.version_id, body.environment, requested_by=actor_id, canary_percent=body.canary_percent, notes=body.notes,
    )
    return to_dict(deployment)


@router.post("/{deployment_id}/approve")
async def approve_deployment(deployment_id: str, actor_id: str = Depends(get_current_actor_id), svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await svc.approve(deployment_id, approved_by=actor_id))


@router.post("/{deployment_id}/reject")
async def reject_deployment(deployment_id: str, body: RejectRequest, actor_id: str = Depends(get_current_actor_id), svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await svc.reject(deployment_id, actor_id=actor_id, reason=body.reason))


@router.post("/{deployment_id}/deploy")
async def deploy(deployment_id: str, actor_id: str = Depends(get_current_actor_id), svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await svc.deploy(deployment_id, actor_id=actor_id))


@router.post("/{deployment_id}/promote-canary")
async def promote_canary(deployment_id: str, body: PromoteCanaryRequest, actor_id: str = Depends(get_current_actor_id), svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await svc.promote_canary(deployment_id, actor_id=actor_id, canary_percent=body.canary_percent))


@router.post("/prompts/{prompt_id}/environments/{environment}/rollback")
async def rollback(prompt_id: str, environment: DeploymentEnvironment, body: RollbackRequest, actor_id: str = Depends(get_current_actor_id), svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await svc.rollback(prompt_id, environment, actor_id=actor_id, target_version_id=body.target_version_id, reason=body.reason))


@router.get("/prompts/{prompt_id}/environments/{environment}/current")
async def get_current(prompt_id: str, environment: DeploymentEnvironment, svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await svc.get_current(prompt_id, environment))


@router.get("/prompts/{prompt_id}/history")
async def deployment_history(prompt_id: str, environment: DeploymentEnvironment | None = None, svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict_list(await svc.history(prompt_id, environment=environment))


@router.put("/environment-config/{environment}")
async def set_environment_config(environment: DeploymentEnvironment, body: EnvConfigRequest, actor_id: str = Depends(get_current_actor_id), svc: DeploymentService = Depends(get_deployment_service)):
    return to_dict(await svc.set_environment_config(body.workspace_id, environment, body.variables, updated_by=actor_id))


@router.get("/environment-config/{environment}")
async def get_environment_config(environment: DeploymentEnvironment, workspace_id: str, svc: DeploymentService = Depends(get_deployment_service)):
    return await svc.get_environment_config(workspace_id, environment)
