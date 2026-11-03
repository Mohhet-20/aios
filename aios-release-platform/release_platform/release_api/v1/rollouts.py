"""Rollout Engine: progressive rollout execution attached to a
deployment."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_rollout_service
from release_platform.release_api.serialization import to_dict, to_dict_list
from release_platform.rollouts.rollout_service import RolloutService

router = APIRouter(prefix="/rollouts", tags=["rollouts"])


class PlanRolloutRequest(BaseModel):
    deployment_id: str
    strategy: str
    target_ref: str | None = None


@router.post("", status_code=201)
async def plan_rollout(
    body: PlanRolloutRequest, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.plan_rollout(tenant_id, **body.model_dump()))


@router.get("/by-deployment/{deployment_id}")
async def list_for_deployment(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict_list(await service.list_for_deployment(tenant_id, deployment_id))


@router.get("/{rollout_id}")
async def get_rollout(
    rollout_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.get_or_404(tenant_id, rollout_id))


@router.post("/{rollout_id}/start")
async def start_rollout(
    rollout_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.start(tenant_id, rollout_id))


@router.post("/{rollout_id}/pause")
async def pause_rollout(
    rollout_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.pause(tenant_id, rollout_id))


@router.post("/{rollout_id}/resume")
async def resume_rollout(
    rollout_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.resume(tenant_id, rollout_id))


class AdvanceRolloutRequest(BaseModel):
    step_pct: float


@router.post("/{rollout_id}/advance")
async def advance_rollout(
    rollout_id: str, body: AdvanceRolloutRequest,
    tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.advance(tenant_id, rollout_id, step_pct=body.step_pct))


@router.post("/{rollout_id}/advance-default-step")
async def advance_default_step(
    rollout_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.advance_by_default_step(tenant_id, rollout_id))


@router.post("/{rollout_id}/complete")
async def complete_rollout(
    rollout_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.complete(tenant_id, rollout_id))


@router.post("/{rollout_id}/abort")
async def abort_rollout(
    rollout_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RolloutService = Depends(get_rollout_service),
):
    return to_dict(await service.abort(tenant_id, rollout_id))
