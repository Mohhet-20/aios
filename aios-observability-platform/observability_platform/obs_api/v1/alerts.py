"""Alerting platform API: rules, firing/evaluation, lifecycle
(acknowledge/resolve/suppress), escalation, maintenance windows, and
notification channels."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.alerts.escalation_service import AlertEscalationService
from observability_platform.alerts.evaluation_service import AlertEvaluationService
from observability_platform.alerts.maintenance_window_service import MaintenanceWindowService
from observability_platform.alerts.rule_service import AlertRuleService
from observability_platform.alerts.suppression_service import AlertSuppressionService
from observability_platform.dependencies.dependencies import (
    get_alert_escalation_service,
    get_alert_evaluation_service,
    get_alert_rule_service,
    get_alert_suppression_service,
    get_current_actor_id,
    get_current_tenant_id,
    get_maintenance_window_service,
    get_repos,
)
from observability_platform.models.alerts import NotificationChannelModel
from observability_platform.obs_api.serialization import to_dict, to_dict_list
from observability_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/alerts", tags=["alerts"])


class CreateRuleRequest(BaseModel):
    name: str
    alert_type: str
    condition: dict
    severity: str = "medium"
    component_id: str | None = None
    metric_name: str | None = None
    evaluation_window_seconds: int | None = None
    escalation_policy_id: str | None = None


@router.post("/rules", status_code=201)
async def create_rule(
    body: CreateRuleRequest, tenant_id: str = Depends(get_current_tenant_id), service: AlertRuleService = Depends(get_alert_rule_service)
):
    return to_dict(await service.create_rule(tenant_id, **body.model_dump()))


@router.get("/rules")
async def list_rules(tenant_id: str = Depends(get_current_tenant_id), service: AlertRuleService = Depends(get_alert_rule_service)):
    return to_dict_list(await service.list_enabled(tenant_id))


class UpdateConditionRequest(BaseModel):
    condition: dict


@router.put("/rules/{rule_id}/condition")
async def update_condition(
    rule_id: str, body: UpdateConditionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: AlertRuleService = Depends(get_alert_rule_service),
):
    return to_dict(await service.update_condition(tenant_id, rule_id, body.condition))


@router.post("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AlertRuleService = Depends(get_alert_rule_service)):
    return to_dict(await service.enable(tenant_id, rule_id))


@router.post("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AlertRuleService = Depends(get_alert_rule_service)):
    return to_dict(await service.disable(tenant_id, rule_id))


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AlertRuleService = Depends(get_alert_rule_service)):
    await service.delete_rule(tenant_id, rule_id)


@router.post("/evaluate/{rule_id}")
async def evaluate_rule(
    rule_id: str, tenant_id: str = Depends(get_current_tenant_id), component_id: str | None = None,
    rule_service: AlertRuleService = Depends(get_alert_rule_service),
    eval_service: AlertEvaluationService = Depends(get_alert_evaluation_service),
    repos: RepositoryRegistry = Depends(get_repos),
):
    rule = await repos.alert_rules.get_or_404(rule_id)
    return to_dict(await eval_service.evaluate_rule(tenant_id, rule, component_id=component_id))


@router.get("")
async def list_alerts(
    tenant_id: str = Depends(get_current_tenant_id), status: str = "firing", limit: int = 200,
    repos: RepositoryRegistry = Depends(get_repos),
):
    return to_dict_list(await repos.alerts.list_by_status(tenant_id, status, limit=limit))


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: AlertSuppressionService = Depends(get_alert_suppression_service),
):
    return to_dict(await service.acknowledge(tenant_id, alert_id, by=actor_id))


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AlertSuppressionService = Depends(get_alert_suppression_service)):
    return to_dict(await service.resolve(tenant_id, alert_id))


class SuppressAlertRequest(BaseModel):
    until: datetime


@router.post("/{alert_id}/suppress")
async def suppress_alert(
    alert_id: str, body: SuppressAlertRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: AlertSuppressionService = Depends(get_alert_suppression_service),
):
    return to_dict(await service.suppress(tenant_id, alert_id, body.until))


@router.post("/{alert_id}/unsuppress")
async def unsuppress_alert(alert_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AlertSuppressionService = Depends(get_alert_suppression_service)):
    return to_dict(await service.unsuppress(tenant_id, alert_id))


@router.post("/{alert_id}/escalate")
async def escalate_alert(alert_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AlertEscalationService = Depends(get_alert_escalation_service)):
    return to_dict_list(await service.escalate(tenant_id, alert_id))


maintenance_router = APIRouter(prefix="/alerts/maintenance-windows", tags=["alerts"])


class ScheduleMaintenanceWindowRequest(BaseModel):
    name: str
    starts_at: datetime
    ends_at: datetime
    component_id: str | None = None
    suppress_alerts: bool = True
    reason: str | None = None


@maintenance_router.post("", status_code=201)
async def schedule_maintenance_window(
    body: ScheduleMaintenanceWindowRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: MaintenanceWindowService = Depends(get_maintenance_window_service),
):
    return to_dict(await service.schedule(tenant_id, **body.model_dump()))


@maintenance_router.post("/{window_id}/activate")
async def activate_window(window_id: str, tenant_id: str = Depends(get_current_tenant_id), service: MaintenanceWindowService = Depends(get_maintenance_window_service)):
    return to_dict(await service.activate(tenant_id, window_id))


@maintenance_router.post("/{window_id}/complete")
async def complete_window(window_id: str, tenant_id: str = Depends(get_current_tenant_id), service: MaintenanceWindowService = Depends(get_maintenance_window_service)):
    return to_dict(await service.complete(tenant_id, window_id))


@maintenance_router.post("/{window_id}/cancel")
async def cancel_window(window_id: str, tenant_id: str = Depends(get_current_tenant_id), service: MaintenanceWindowService = Depends(get_maintenance_window_service)):
    return to_dict(await service.cancel(tenant_id, window_id))


channels_router = APIRouter(prefix="/alerts/channels", tags=["alerts"])


class CreateChannelRequest(BaseModel):
    name: str
    channel_type: str
    config: dict | None = None


@channels_router.post("", status_code=201)
async def create_channel(body: CreateChannelRequest, tenant_id: str = Depends(get_current_tenant_id), repos: RepositoryRegistry = Depends(get_repos)):
    channel = NotificationChannelModel(tenant_id=tenant_id, name=body.name, channel_type=body.channel_type, config=body.config or {})
    return to_dict(await repos.notification_channels.add(channel))


@channels_router.get("")
async def list_channels(tenant_id: str = Depends(get_current_tenant_id), repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.notification_channels.list_enabled(tenant_id))
