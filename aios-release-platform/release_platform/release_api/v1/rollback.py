"""Rollback Engine: rollback actions across the 8 declared types."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_rollback_service
from release_platform.release_api.serialization import to_dict, to_dict_list
from release_platform.rollback.rollback_service import RollbackService

router = APIRouter(prefix="/rollbacks", tags=["rollback"])


class InitiateRollbackRequest(BaseModel):
    deployment_id: str
    rollback_type: str
    reason: str = ""
    initiated_by: str | None = None


@router.post("", status_code=201)
async def initiate_rollback(
    body: InitiateRollbackRequest, tenant_id: str = Depends(get_current_tenant_id), service: RollbackService = Depends(get_rollback_service),
):
    return to_dict(await service.initiate_rollback(tenant_id, **body.model_dump()))


@router.get("/by-deployment/{deployment_id}")
async def list_for_deployment(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RollbackService = Depends(get_rollback_service),
):
    return to_dict_list(await service.list_for_deployment(tenant_id, deployment_id))


@router.get("/{rollback_id}")
async def get_rollback(
    rollback_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RollbackService = Depends(get_rollback_service),
):
    return to_dict(await service.get_or_404(tenant_id, rollback_id))


@router.post("/{rollback_id}/start")
async def start_rollback(
    rollback_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RollbackService = Depends(get_rollback_service),
):
    return to_dict(await service.start(tenant_id, rollback_id))


@router.post("/{rollback_id}/complete")
async def complete_rollback(
    rollback_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RollbackService = Depends(get_rollback_service),
):
    return to_dict(await service.complete(tenant_id, rollback_id))


@router.post("/{rollback_id}/fail")
async def fail_rollback(
    rollback_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RollbackService = Depends(get_rollback_service),
):
    return to_dict(await service.fail(tenant_id, rollback_id))
