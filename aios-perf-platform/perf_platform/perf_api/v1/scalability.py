"""GPU / Scalability: pool registration, utilization reporting, and
underutilized-pool discovery for cost-reduction candidates."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from perf_platform.dependencies.dependencies import get_current_tenant_id, get_gpu_pool_service
from perf_platform.perf_api.serialization import to_dict, to_dict_list
from perf_platform.scalability.gpu_service import GpuPoolService

router = APIRouter(prefix="/gpu-pools", tags=["scalability"])


class RegisterGpuPoolRequest(BaseModel):
    name: str
    pool_type: str
    gpu_count: int = 1


@router.post("", status_code=201)
async def register_pool(
    body: RegisterGpuPoolRequest, tenant_id: str = Depends(get_current_tenant_id), service: GpuPoolService = Depends(get_gpu_pool_service),
):
    return to_dict(await service.register_pool(tenant_id, **body.model_dump()))


@router.get("")
async def list_pools(
    pool_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: GpuPoolService = Depends(get_gpu_pool_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, pool_type=pool_type))


@router.get("/underutilized")
async def underutilized(
    threshold_pct: float = 20.0, tenant_id: str = Depends(get_current_tenant_id), service: GpuPoolService = Depends(get_gpu_pool_service),
):
    return to_dict_list(await service.underutilized_pools(tenant_id, threshold_pct=threshold_pct))


class ReportUtilizationRequest(BaseModel):
    utilization_pct: float


@router.post("/{pool_id}/utilization")
async def report_utilization(
    pool_id: str, body: ReportUtilizationRequest, tenant_id: str = Depends(get_current_tenant_id), service: GpuPoolService = Depends(get_gpu_pool_service),
):
    return to_dict(await service.report_utilization(tenant_id, pool_id, body.utilization_pct))


@router.post("/{pool_id}/activate")
async def activate(pool_id: str, tenant_id: str = Depends(get_current_tenant_id), service: GpuPoolService = Depends(get_gpu_pool_service)):
    return to_dict(await service.activate(tenant_id, pool_id))


@router.post("/{pool_id}/deactivate")
async def deactivate(pool_id: str, tenant_id: str = Depends(get_current_tenant_id), service: GpuPoolService = Depends(get_gpu_pool_service)):
    return to_dict(await service.deactivate(tenant_id, pool_id))
