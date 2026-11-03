"""KPI Engine: KPI definitions, health evaluation, and snapshot
history."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dependencies.dependencies import get_current_tenant_id, get_kpi_service, get_kpi_snapshot_service
from analytics_platform.kpis.kpi_service import KpiService
from analytics_platform.kpis.snapshot_service import KpiSnapshotService

router = APIRouter(prefix="/kpis", tags=["kpis"])
snapshots_router = APIRouter(prefix="/kpis", tags=["kpis"])


class RegisterKpiRequest(BaseModel):
    name: str
    scope: str
    metric_key: str
    target_value: float
    higher_is_better: bool = True
    threshold_warning: float | None = None
    threshold_critical: float | None = None


@router.post("", status_code=201)
async def register_kpi(
    body: RegisterKpiRequest, tenant_id: str = Depends(get_current_tenant_id), service: KpiService = Depends(get_kpi_service),
):
    return to_dict(await service.register_kpi(tenant_id, **body.model_dump()))


@router.get("")
async def list_kpis(
    scope: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: KpiService = Depends(get_kpi_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, scope=scope))


@router.get("/{kpi_id}")
async def get_kpi(
    kpi_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KpiService = Depends(get_kpi_service),
):
    return to_dict(await service.get_or_404(tenant_id, kpi_id))


@router.post("/{kpi_id}/archive")
async def archive_kpi(
    kpi_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KpiService = Depends(get_kpi_service),
):
    return to_dict(await service.archive_kpi(tenant_id, kpi_id))


@router.post("/{kpi_id}/reactivate")
async def reactivate_kpi(
    kpi_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KpiService = Depends(get_kpi_service),
):
    return to_dict(await service.reactivate_kpi(tenant_id, kpi_id))


class RecordSnapshotRequest(BaseModel):
    value: float


@snapshots_router.post("/{kpi_id}/snapshots", status_code=201)
async def record_snapshot(
    kpi_id: str, body: RecordSnapshotRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: KpiSnapshotService = Depends(get_kpi_snapshot_service),
):
    return to_dict(await service.record_snapshot(tenant_id, kpi_id, value=body.value))


@snapshots_router.get("/{kpi_id}/snapshots")
async def list_snapshots(
    kpi_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KpiSnapshotService = Depends(get_kpi_snapshot_service),
):
    return to_dict_list(await service.history(tenant_id, kpi_id))


@snapshots_router.get("/{kpi_id}/trend")
async def get_trend(
    kpi_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KpiSnapshotService = Depends(get_kpi_snapshot_service),
):
    return {"trend": await service.trend(tenant_id, kpi_id)}
