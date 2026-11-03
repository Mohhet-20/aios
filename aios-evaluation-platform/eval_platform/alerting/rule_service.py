"""AlertRuleService: CRUD for a standing alert condition — a metric key,
comparator, and threshold (optionally scoped to a rolling window),
plus a notification policy describing who/what to notify when it
trips. `AlertEvaluator` (in `evaluator.py`) is what actually checks a
rule's condition against an observed value and opens an `Alert`."""
from __future__ import annotations

from eval_platform.core.exceptions import AlertRuleError
from eval_platform.core.pagination import Page, PaginationParams
from eval_platform.domain.enums import AlertCategory, AlertComparator, AlertSeverity
from eval_platform.models.alert import AlertRuleModel
from eval_platform.repositories.registry import RepositoryRegistry

_VALID_CATEGORIES = {c.value for c in AlertCategory}
_VALID_SEVERITIES = {s.value for s in AlertSeverity}
_VALID_COMPARATORS = {c.value for c in AlertComparator}


def _validate_condition(condition: dict) -> None:
    if "metric" not in condition or not condition["metric"]:
        raise AlertRuleError("condition must declare a 'metric'")
    comparator = condition.get("comparator")
    if comparator not in _VALID_COMPARATORS:
        raise AlertRuleError(f"condition.comparator must be one of {sorted(_VALID_COMPARATORS)}, got {comparator!r}")
    if "threshold" not in condition or not isinstance(condition["threshold"], (int, float)):
        raise AlertRuleError("condition must declare a numeric 'threshold'")
    window = condition.get("window_minutes")
    if window is not None and (not isinstance(window, (int, float)) or window <= 0):
        raise AlertRuleError("condition.window_minutes must be a positive number when present")


class AlertRuleService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_rule(
        self, workspace_id: str, *, name: str, category: str, severity: str, condition: dict,
        notification_policy: dict | None = None,
    ) -> AlertRuleModel:
        if category not in _VALID_CATEGORIES:
            raise AlertRuleError(f"unknown category '{category}' (must be one of {sorted(_VALID_CATEGORIES)})")
        if severity not in _VALID_SEVERITIES:
            raise AlertRuleError(f"unknown severity '{severity}' (must be one of {sorted(_VALID_SEVERITIES)})")
        _validate_condition(condition)

        return await self.repos.alert_rules.add(AlertRuleModel(
            workspace_id=workspace_id, name=name, category=category, severity=severity, condition=condition,
            notification_policy=notification_policy or {},
        ))

    async def get_rule(self, rule_id: str) -> AlertRuleModel:
        return await self.repos.alert_rules.get_or_404(rule_id)

    async def list_rules(self, workspace_id: str, params: PaginationParams) -> Page[AlertRuleModel]:
        return await self.repos.alert_rules.paginated_list(params, filters={"workspace_id": workspace_id})

    async def list_active_rules(self, workspace_id: str) -> list[AlertRuleModel]:
        return await self.repos.alert_rules.list_active_for_workspace(workspace_id)

    async def update_rule(self, rule_id: str, **fields) -> AlertRuleModel:
        rule = await self.repos.alert_rules.get_or_404(rule_id)
        allowed = {"name", "severity", "condition", "notification_policy"}
        unknown = set(fields) - allowed
        if unknown:
            raise AlertRuleError(f"cannot update fields: {sorted(unknown)}")
        if "severity" in fields and fields["severity"] not in _VALID_SEVERITIES:
            raise AlertRuleError(f"unknown severity '{fields['severity']}'")
        if "condition" in fields:
            _validate_condition(fields["condition"])
        for key, value in fields.items():
            setattr(rule, key, value)
        return await self.repos.alert_rules.update(rule)

    async def set_active(self, rule_id: str, is_active: bool) -> AlertRuleModel:
        rule = await self.repos.alert_rules.get_or_404(rule_id)
        rule.is_active = is_active
        return await self.repos.alert_rules.update(rule)

    async def delete_rule(self, rule_id: str) -> None:
        rule = await self.repos.alert_rules.get_or_404(rule_id)
        await self.repos.alert_rules.delete(rule, hard=True)
