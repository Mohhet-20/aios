"""Alert rule CRUD. `condition` is a small typed-by-convention JSON
blob interpreted by `AlertEvaluationService` based on `alert_type`:
threshold rules use `{"metric_name": ..., "operator": "gt"|"lt"|"gte"|"lte"|"eq", "value": <number>}`,
anomaly rules use `{"metric_name": ..., "baseline_window_points": <int>, "deviation_multiplier": <number>}`
(a simple standard-deviation-multiple check — an honestly-scoped
approximation, not a real ML anomaly detector; see
`evaluation_service.py`'s module docstring), and every other alert
type (availability/latency/resource/security/workflow_failure/
agent_failure/memory_failure/database/custom) is evaluated the same
way as threshold against whatever metric name callers wire it to —
this build doesn't hardcode per-domain evaluation logic, since that
would mean a code change every time a new AIOS subsystem wants to
define its own alert."""
from __future__ import annotations

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import AlertRuleError, ValidationError
from observability_platform.domain.enums import AlertSeverity, AlertType
from observability_platform.models.alerts import AlertRuleModel
from observability_platform.repositories.registry import RepositoryRegistry


class AlertRuleService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_rule(
        self,
        tenant_id: str,
        *,
        name: str,
        alert_type: str,
        condition: dict,
        severity: str = AlertSeverity.MEDIUM.value,
        component_id: str | None = None,
        metric_name: str | None = None,
        evaluation_window_seconds: int | None = None,
        escalation_policy_id: str | None = None,
    ) -> AlertRuleModel:
        if alert_type not in {t.value for t in AlertType}:
            raise ValidationError(f"Unknown alert type '{alert_type}'")
        if severity not in {s.value for s in AlertSeverity}:
            raise ValidationError(f"Unknown severity '{severity}'")
        if not condition:
            raise AlertRuleError("Alert rule condition cannot be empty")
        rule = AlertRuleModel(
            tenant_id=tenant_id, name=name, alert_type=alert_type, severity=severity, condition=condition,
            component_id=component_id, metric_name=metric_name,
            evaluation_window_seconds=evaluation_window_seconds or self.settings.alert_evaluation_interval_seconds,
            escalation_policy_id=escalation_policy_id,
        )
        return await self.repos.alert_rules.add(rule)

    async def update_condition(self, tenant_id: str, rule_id: str, condition: dict) -> AlertRuleModel:
        rule = await self.repos.alert_rules.get_or_404(rule_id)
        if not condition:
            raise AlertRuleError("Alert rule condition cannot be empty")
        rule.condition = condition
        return await self.repos.alert_rules.update(rule)

    async def enable(self, tenant_id: str, rule_id: str) -> AlertRuleModel:
        rule = await self.repos.alert_rules.get_or_404(rule_id)
        rule.is_enabled = True
        return await self.repos.alert_rules.update(rule)

    async def disable(self, tenant_id: str, rule_id: str) -> AlertRuleModel:
        rule = await self.repos.alert_rules.get_or_404(rule_id)
        rule.is_enabled = False
        return await self.repos.alert_rules.update(rule)

    async def list_enabled(self, tenant_id: str) -> list[AlertRuleModel]:
        return await self.repos.alert_rules.list_enabled(tenant_id)

    async def delete_rule(self, tenant_id: str, rule_id: str) -> None:
        rule = await self.repos.alert_rules.get_or_404(rule_id)
        await self.repos.alert_rules.delete(rule)
