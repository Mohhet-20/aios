"""Reliability Engineering: SLO definitions and reliability metric
snapshot recording."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import get_current_tenant_id, get_reliability_snapshot_service, get_slo_service
from quality_platform.qa_api.serialization import to_dict, to_dict_list
from quality_platform.reliability.reliability_snapshot_service import ReliabilitySnapshotService
from quality_platform.reliability.slo_service import SloService

router = APIRouter(prefix="/slos", tags=["reliability"])
snapshots_router = APIRouter(prefix="/reliability-snapshots", tags=["reliability"])


class RegisterSloRequest(BaseModel):
    name: str
    service_ref: str
    target_pct: float | None = None
    window_days: int | None = None


@router.post("", status_code=201)
async def register_slo(
    body: RegisterSloRequest, tenant_id: str = Depends(get_current_tenant_id), service: SloService = Depends(get_slo_service),
):
    return to_dict(await service.register_slo(tenant_id, **body.model_dump()))


@router.get("")
async def list_slos(
    service_ref: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: SloService = Depends(get_slo_service),
):
    return to_dict_list(await service.list_slos(tenant_id, service_ref=service_ref))


@router.get("/{slo_id}")
async def get_slo(
    slo_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SloService = Depends(get_slo_service),
):
    return to_dict(await service.get_or_404(tenant_id, slo_id))


class EvaluateSloRequest(BaseModel):
    current_pct: float | None = None


@router.post("/{slo_id}/evaluate")
async def evaluate_slo(
    slo_id: str, body: EvaluateSloRequest, tenant_id: str = Depends(get_current_tenant_id), service: SloService = Depends(get_slo_service),
):
    return to_dict(await service.evaluate_slo(tenant_id, slo_id, current_pct=body.current_pct))


class RecordSnapshotRequest(BaseModel):
    service_ref: str
    metric_type: str
    value: float


@snapshots_router.post("", status_code=201)
async def record_snapshot(
    body: RecordSnapshotRequest, tenant_id: str = Depends(get_current_tenant_id), service: ReliabilitySnapshotService = Depends(get_reliability_snapshot_service),
):
    return to_dict(await service.record_snapshot(tenant_id, body.service_ref, metric_type=body.metric_type, value=body.value))


@snapshots_router.get("")
async def list_snapshots(
    service_ref: str, metric_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: ReliabilitySnapshotService = Depends(get_reliability_snapshot_service),
):
    return to_dict_list(await service.list_for_service(tenant_id, service_ref, metric_type=metric_type))
