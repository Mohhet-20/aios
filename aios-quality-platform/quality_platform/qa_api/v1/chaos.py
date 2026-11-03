"""Chaos Engineering Platform: failure-injection experiment lifecycle
across the twelve failure types, capped by blast radius."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.chaos.chaos_experiment_service import ChaosExperimentService
from quality_platform.dependencies.dependencies import get_chaos_experiment_service, get_current_tenant_id
from quality_platform.qa_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/chaos-experiments", tags=["chaos"])


class RequestExperimentRequest(BaseModel):
    failure_type: str
    target_ref: str
    blast_radius_pct: float
    config: dict | None = None


@router.post("", status_code=201)
async def request_experiment(
    body: RequestExperimentRequest, tenant_id: str = Depends(get_current_tenant_id), service: ChaosExperimentService = Depends(get_chaos_experiment_service),
):
    return to_dict(await service.request_experiment(
        tenant_id, failure_type=body.failure_type, target_ref=body.target_ref, blast_radius_pct=body.blast_radius_pct, config=body.config,
    ))


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ChaosExperimentService = Depends(get_chaos_experiment_service),
):
    return to_dict(await service.get_or_404(tenant_id, experiment_id))


@router.post("/{experiment_id}/start")
async def start_experiment(
    experiment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ChaosExperimentService = Depends(get_chaos_experiment_service),
):
    return to_dict(await service.start(tenant_id, experiment_id))


class FinishExperimentRequest(BaseModel):
    recovered: bool
    recovery_time_seconds: float | None = None


@router.post("/{experiment_id}/finish")
async def finish_experiment(
    experiment_id: str, body: FinishExperimentRequest, tenant_id: str = Depends(get_current_tenant_id), service: ChaosExperimentService = Depends(get_chaos_experiment_service),
):
    return to_dict(await service.finish_experiment(tenant_id, experiment_id, recovered=body.recovered, recovery_time_seconds=body.recovery_time_seconds))


@router.get("")
async def list_experiments(
    failure_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: ChaosExperimentService = Depends(get_chaos_experiment_service),
):
    return to_dict_list(await service.list_experiments(tenant_id, failure_type=failure_type))
