"""Quality platform observability: trend snapshot recording/querying
across the eight metric types the prompt specifies."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import get_current_tenant_id, get_trend_service
from quality_platform.observability.trend_service import TrendService
from quality_platform.qa_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/trends", tags=["observability"])


class RecordSnapshotRequest(BaseModel):
    metric_type: str
    value: float
    subject_ref: str | None = None


@router.post("", status_code=201)
async def record_snapshot(
    body: RecordSnapshotRequest, tenant_id: str = Depends(get_current_tenant_id), service: TrendService = Depends(get_trend_service),
):
    return to_dict(await service.record_snapshot(tenant_id, metric_type=body.metric_type, value=body.value, subject_ref=body.subject_ref))


@router.get("/{metric_type}")
async def list_trend(
    metric_type: str, subject_ref: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: TrendService = Depends(get_trend_service),
):
    return to_dict_list(await service.list_trend(tenant_id, metric_type, subject_ref=subject_ref))


@router.get("/{metric_type}/direction")
async def get_direction(
    metric_type: str, subject_ref: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: TrendService = Depends(get_trend_service),
):
    return {"direction": await service.direction_for(tenant_id, metric_type, subject_ref=subject_ref)}
