"""AlertService: opens, acknowledges, resolves, and reopens `Alert`
rows — reusing the `Alert` domain entity's OPEN -> ACKNOWLEDGED ->
RESOLVED state machine from `domain/entities.py`. An alert can be
opened standalone (`alert_rule_id=None`, e.g. a one-off safety flag
raised inline during evaluation scoring) or by `AlertEvaluator` when a
standing rule trips."""
from __future__ import annotations

from eval_platform.core.exceptions import AlertRuleError
from eval_platform.domain.entities import Alert
from eval_platform.domain.enums import AlertCategory, AlertSeverity, AlertStatus
from eval_platform.models.alert import AlertModel
from eval_platform.repositories.registry import RepositoryRegistry

_VALID_CATEGORIES = {c.value for c in AlertCategory}
_VALID_SEVERITIES = {s.value for s in AlertSeverity}


def _alert_to_domain(model: AlertModel) -> Alert:
    return Alert(
        id=model.id, workspace_id=model.workspace_id, category=model.category, severity=model.severity,
        message=model.message, status=AlertStatus(model.status), context=dict(model.context or {}),
        acknowledged_by=model.acknowledged_by, acknowledged_at=model.acknowledged_at,
        resolved_by=model.resolved_by, resolved_at=model.resolved_at,
    )


def _apply_alert_to_model(entity: Alert, model: AlertModel) -> None:
    model.status = entity.status.value
    model.acknowledged_by = entity.acknowledged_by
    model.acknowledged_at = entity.acknowledged_at
    model.resolved_by = entity.resolved_by
    model.resolved_at = entity.resolved_at


class AlertService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def trigger_alert(
        self, workspace_id: str, *, category: str, severity: str, message: str,
        alert_rule_id: str | None = None, context: dict | None = None,
    ) -> AlertModel:
        if category not in _VALID_CATEGORIES:
            raise AlertRuleError(f"unknown category '{category}' (must be one of {sorted(_VALID_CATEGORIES)})")
        if severity not in _VALID_SEVERITIES:
            raise AlertRuleError(f"unknown severity '{severity}' (must be one of {sorted(_VALID_SEVERITIES)})")
        return await self.repos.alerts.add(AlertModel(
            workspace_id=workspace_id, alert_rule_id=alert_rule_id, category=category, severity=severity,
            message=message, context=context or {},
        ))

    async def get_alert(self, alert_id: str) -> AlertModel:
        return await self.repos.alerts.get_or_404(alert_id)

    async def list_alerts(self, workspace_id: str, *, status: str | None = None, category: str | None = None) -> list[AlertModel]:
        return await self.repos.alerts.list_for_workspace(workspace_id, status=status, category=category)

    async def list_open_for_rule(self, alert_rule_id: str) -> list[AlertModel]:
        return await self.repos.alerts.list_open_for_rule(alert_rule_id)

    async def acknowledge(self, alert_id: str, *, by: str) -> AlertModel:
        return await self._apply_transition(alert_id, "acknowledge", by=by)

    async def resolve(self, alert_id: str, *, by: str) -> AlertModel:
        return await self._apply_transition(alert_id, "resolve", by=by)

    async def reopen(self, alert_id: str) -> AlertModel:
        return await self._apply_transition(alert_id, "reopen")

    async def _apply_transition(self, alert_id: str, transition: str, **kwargs) -> AlertModel:
        model = await self.repos.alerts.get_or_404(alert_id)
        entity = _alert_to_domain(model)
        getattr(entity, transition)(**kwargs)
        _apply_alert_to_model(entity, model)
        return await self.repos.alerts.update(model)
