"""Cost Intelligence Engine: cost recording, per-entity totals, budget
management and utilization."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from perf_platform.cost_intelligence.cost_service import BudgetService, CostRecordService
from perf_platform.dependencies.dependencies import get_budget_service, get_cost_record_service, get_current_tenant_id
from perf_platform.perf_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/cost", tags=["cost"])
budgets_router = APIRouter(prefix="/budgets", tags=["cost"])


class RecordCostRequest(BaseModel):
    category: str
    entity_type: str
    entity_id: str
    amount_usd: float
    unit_count: float = 0.0
    extra: dict | None = None


@router.post("/records", status_code=201)
async def record_cost(
    body: RecordCostRequest, tenant_id: str = Depends(get_current_tenant_id), service: CostRecordService = Depends(get_cost_record_service),
):
    return to_dict(await service.record(tenant_id, **body.model_dump()))


@router.get("/records")
async def list_records(
    category: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: CostRecordService = Depends(get_cost_record_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, category=category))


@router.get("/records/{entity_type}/{entity_id}/total")
async def total_for_entity(
    entity_type: str, entity_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CostRecordService = Depends(get_cost_record_service),
):
    return {"entity_type": entity_type, "entity_id": entity_id, "total_usd": await service.total_for_entity(tenant_id, entity_type, entity_id)}


class SetBudgetRequest(BaseModel):
    entity_type: str
    entity_id: str
    limit_usd: float
    period: str = "monthly"


@budgets_router.put("")
async def set_budget(
    body: SetBudgetRequest, tenant_id: str = Depends(get_current_tenant_id), service: BudgetService = Depends(get_budget_service),
):
    return to_dict(await service.set_budget(tenant_id, **body.model_dump()))


@budgets_router.get("/{entity_type}/{entity_id}")
async def get_budget(
    entity_type: str, entity_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BudgetService = Depends(get_budget_service),
):
    return to_dict(await service.get_budget_or_404(tenant_id, entity_type, entity_id))


@budgets_router.get("/{entity_type}/{entity_id}/utilization")
async def budget_utilization(
    entity_type: str, entity_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BudgetService = Depends(get_budget_service),
):
    return {"utilization_pct": await service.utilization_pct(tenant_id, entity_type, entity_id)}


@budgets_router.post("/{entity_type}/{entity_id}/check-alerts")
async def check_alerts(
    entity_type: str, entity_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BudgetService = Depends(get_budget_service),
):
    return to_dict_list(await service.check_and_alert(tenant_id, entity_type=entity_type, entity_id=entity_id))
