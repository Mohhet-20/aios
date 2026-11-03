"""Risk Engine API: current (decayed) score, recording new
factor-weighted scores, single-event convenience scoring, periodic
decay refresh, history, and top-risky-entities."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import get_current_tenant_id, get_risk_engine_service
from security_platform.risk_engine.risk_service import RiskEngineService
from security_platform.sec_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/{entity_type}/{entity_id}/current")
async def current_score(entity_type: str, entity_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RiskEngineService = Depends(get_risk_engine_service)):
    return {"score": await service.current_score(tenant_id, entity_type, entity_id)}


class RecordScoreRequest(BaseModel):
    factors: dict[str, float]
    base_on_current: bool = True


@router.post("/{entity_type}/{entity_id}/record", status_code=201)
async def record_score(
    entity_type: str, entity_id: str, body: RecordScoreRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: RiskEngineService = Depends(get_risk_engine_service),
):
    return to_dict(await service.record_score(tenant_id, entity_type, entity_id, body.factors, base_on_current=body.base_on_current))


class ApplyEventRequest(BaseModel):
    event_name: str
    weight: float


@router.post("/{entity_type}/{entity_id}/events", status_code=201)
async def apply_event(
    entity_type: str, entity_id: str, body: ApplyEventRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: RiskEngineService = Depends(get_risk_engine_service),
):
    return to_dict(await service.apply_event(tenant_id, entity_type, entity_id, body.event_name, body.weight))


@router.post("/{entity_type}/{entity_id}/refresh-decay")
async def refresh_decay(entity_type: str, entity_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RiskEngineService = Depends(get_risk_engine_service)):
    return to_dict(await service.refresh_decay(tenant_id, entity_type, entity_id))


@router.get("/{entity_type}/{entity_id}/history")
async def history(entity_type: str, entity_id: str, limit: int = 100, tenant_id: str = Depends(get_current_tenant_id), service: RiskEngineService = Depends(get_risk_engine_service)):
    return to_dict_list(await service.history(tenant_id, entity_type, entity_id, limit=limit))


@router.get("/{entity_type}/top")
async def top_risky(entity_type: str, limit: int = 20, tenant_id: str = Depends(get_current_tenant_id), service: RiskEngineService = Depends(get_risk_engine_service)):
    return to_dict_list(await service.top_risky(tenant_id, entity_type, limit=limit))
