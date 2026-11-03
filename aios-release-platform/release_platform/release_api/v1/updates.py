"""Update Infrastructure: update job lifecycle and version
compatibility checks."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_update_job_service
from release_platform.release_api.serialization import to_dict, to_dict_list
from release_platform.updates.update_service import UpdateJobService

router = APIRouter(prefix="/update-jobs", tags=["updates"])


class ScheduleUpdateRequest(BaseModel):
    target_ref: str
    update_type: str
    to_version: str
    from_version: str | None = None
    scheduled_at: datetime | None = None


@router.post("", status_code=201)
async def schedule_update(
    body: ScheduleUpdateRequest, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict(await service.schedule_update(tenant_id, **body.model_dump()))


@router.get("/by-target/{target_ref}")
async def list_for_target(
    target_ref: str, limit: int = 100, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict_list(await service.list_for_target(tenant_id, target_ref, limit=limit))


@router.get("/{job_id}")
async def get_job(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict(await service.get_or_404(tenant_id, job_id))


@router.post("/{job_id}/start-download")
async def start_download(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict(await service.start_download(tenant_id, job_id))


@router.post("/{job_id}/begin-apply")
async def begin_apply(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict(await service.begin_apply(tenant_id, job_id))


@router.post("/{job_id}/mark-applied")
async def mark_applied(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict(await service.mark_applied(tenant_id, job_id))


class FailUpdateRequest(BaseModel):
    reason: str


@router.post("/{job_id}/fail")
async def fail_update(
    job_id: str, body: FailUpdateRequest, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict(await service.fail(tenant_id, job_id, reason=body.reason))


@router.post("/{job_id}/mark-rolled-back")
async def mark_rolled_back(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    return to_dict(await service.mark_rolled_back(tenant_id, job_id))


class CheckCompatibilityRequest(BaseModel):
    platform_version: str
    component_ref: str
    candidate_version: str


@router.post("/check-compatibility")
async def check_version_compatibility(
    body: CheckCompatibilityRequest, tenant_id: str = Depends(get_current_tenant_id), service: UpdateJobService = Depends(get_update_job_service),
):
    await service.check_version_compatibility(tenant_id, **body.model_dump())
    return {"compatible": True}
