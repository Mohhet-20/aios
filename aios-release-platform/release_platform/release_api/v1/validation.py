"""Deployment Validation: post-deploy health checks across the 10
declared targets."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_health_check_service
from release_platform.release_api.serialization import to_dict, to_dict_list
from release_platform.validation.health_check_service import HealthCheckService

router = APIRouter(prefix="/health-checks", tags=["validation"])


class RecordCheckRequest(BaseModel):
    deployment_id: str
    target: str
    status: str
    details: dict | None = None


@router.post("", status_code=201)
async def record_check(
    body: RecordCheckRequest, tenant_id: str = Depends(get_current_tenant_id), service: HealthCheckService = Depends(get_health_check_service),
):
    return to_dict(await service.record_check(tenant_id, **body.model_dump()))


@router.post("/run-all/{deployment_id}")
async def run_all_checks(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: HealthCheckService = Depends(get_health_check_service),
):
    # No checker callable is supplied through the HTTP surface — every
    # target is recorded as `degraded` per `run_all_checks`'s documented
    # honest-gap default, mirroring `generation-jobs/{id}/run` in the
    # Documentation Platform.
    return to_dict_list(await service.run_all_checks(tenant_id, deployment_id))


@router.get("/by-deployment/{deployment_id}")
async def list_for_deployment(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: HealthCheckService = Depends(get_health_check_service),
):
    return to_dict_list(await service.list_for_deployment(tenant_id, deployment_id))


@router.get("/by-deployment/{deployment_id}/is-healthy")
async def is_deployment_healthy(
    deployment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: HealthCheckService = Depends(get_health_check_service),
):
    return {"deployment_id": deployment_id, "healthy": await service.is_deployment_healthy(tenant_id, deployment_id)}
