"""Alerting: standing rule CRUD, the OPEN -> ACKNOWLEDGED -> RESOLVED
incident lifecycle, and evaluating a rule/all active rules against
caller-supplied observed values."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.alerting.alert_service import AlertService
from eval_platform.alerting.evaluator import AlertEvaluator
from eval_platform.alerting.rule_service import AlertRuleService
from eval_platform.core.pagination import PaginationParams
from eval_platform.dependencies.dependencies import get_alert_evaluator, get_alert_rule_service, get_alert_service
from eval_platform.eval_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/alerting", tags=["alerting"])


class CreateRuleRequest(BaseModel):
    workspace_id: str
    name: str
    category: str
    severity: str
    condition: dict
    notification_policy: dict | None = None


class UpdateRuleRequest(BaseModel):
    name: str | None = None
    severity: str | None = None
    condition: dict | None = None
    notification_policy: dict | None = None


class TriggerAlertRequest(BaseModel):
    workspace_id: str
    category: str
    severity: str
    message: str
    context: dict | None = None


class EvaluateActiveRulesRequest(BaseModel):
    observed_values: dict[str, float]


@router.post("/rules", status_code=201)
async def create_rule(body: CreateRuleRequest, service: AlertRuleService = Depends(get_alert_rule_service)):
    return to_dict(await service.create_rule(
        body.workspace_id, name=body.name, category=body.category, severity=body.severity, condition=body.condition,
        notification_policy=body.notification_policy,
    ))


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str, service: AlertRuleService = Depends(get_alert_rule_service)):
    return to_dict(await service.get_rule(rule_id))


@router.get("/rules")
async def list_rules(workspace_id: str, page: int = 1, page_size: int = 50, service: AlertRuleService = Depends(get_alert_rule_service)):
    result = await service.list_rules(workspace_id, PaginationParams(page=page, page_size=page_size))
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size}


@router.patch("/rules/{rule_id}")
async def update_rule(rule_id: str, body: UpdateRuleRequest, service: AlertRuleService = Depends(get_alert_rule_service)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    return to_dict(await service.update_rule(rule_id, **fields))


@router.post("/rules/{rule_id}/active")
async def set_rule_active(rule_id: str, is_active: bool, service: AlertRuleService = Depends(get_alert_rule_service)):
    return to_dict(await service.set_active(rule_id, is_active))


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, service: AlertRuleService = Depends(get_alert_rule_service)):
    await service.delete_rule(rule_id)


@router.post("/rules/{rule_id}/evaluate")
async def evaluate_rule(rule_id: str, observed_value: float, evaluator: AlertEvaluator = Depends(get_alert_evaluator), rule_service: AlertRuleService = Depends(get_alert_rule_service)):
    rule = await rule_service.get_rule(rule_id)
    alert = await evaluator.evaluate_rule(rule, observed_value)
    return to_dict(alert)


@router.post("/rules/evaluate-active")
async def evaluate_active_rules(workspace_id: str, body: EvaluateActiveRulesRequest, evaluator: AlertEvaluator = Depends(get_alert_evaluator)):
    return to_dict_list(await evaluator.evaluate_active_rules(workspace_id, body.observed_values))


# -- alerts ------------------------------------------------------------------------------

@router.post("/alerts", status_code=201)
async def trigger_alert(body: TriggerAlertRequest, service: AlertService = Depends(get_alert_service)):
    return to_dict(await service.trigger_alert(
        body.workspace_id, category=body.category, severity=body.severity, message=body.message, context=body.context,
    ))


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str, service: AlertService = Depends(get_alert_service)):
    return to_dict(await service.get_alert(alert_id))


@router.get("/alerts")
async def list_alerts(workspace_id: str, status: str | None = None, category: str | None = None, service: AlertService = Depends(get_alert_service)):
    return to_dict_list(await service.list_alerts(workspace_id, status=status, category=category))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, by: str, service: AlertService = Depends(get_alert_service)):
    return to_dict(await service.acknowledge(alert_id, by=by))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, by: str, service: AlertService = Depends(get_alert_service)):
    return to_dict(await service.resolve(alert_id, by=by))


@router.post("/alerts/{alert_id}/reopen")
async def reopen_alert(alert_id: str, service: AlertService = Depends(get_alert_service)):
    return to_dict(await service.reopen(alert_id))
