"""AlertEvaluator: checks an `AlertRuleModel`'s condition
(metric/comparator/threshold) against a genuinely observed value —
this platform's own observability/metrics/analytics layers are the
only legitimate source for that value; the evaluator itself never
computes or guesses one. Deduplicates by rule: if an alert from this
rule is already open (not yet resolved), a repeated trip doesn't spawn
a second incident."""
from __future__ import annotations

from eval_platform.alerting.alert_service import AlertService
from eval_platform.domain.enums import AlertComparator
from eval_platform.models.alert import AlertModel, AlertRuleModel
from eval_platform.repositories.registry import RepositoryRegistry

_COMPARATORS = {
    AlertComparator.GT.value: lambda observed, threshold: observed > threshold,
    AlertComparator.GTE.value: lambda observed, threshold: observed >= threshold,
    AlertComparator.LT.value: lambda observed, threshold: observed < threshold,
    AlertComparator.LTE.value: lambda observed, threshold: observed <= threshold,
    AlertComparator.EQ.value: lambda observed, threshold: observed == threshold,
    AlertComparator.NEQ.value: lambda observed, threshold: observed != threshold,
}


class AlertEvaluator:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.alerts = AlertService(repos)

    def evaluate_condition(self, rule: AlertRuleModel, observed_value: float) -> bool:
        comparator = _COMPARATORS[rule.condition["comparator"]]
        return comparator(observed_value, rule.condition["threshold"])

    async def evaluate_rule(self, rule: AlertRuleModel, observed_value: float) -> AlertModel | None:
        if not rule.is_active:
            return None
        if not self.evaluate_condition(rule, observed_value):
            return None

        existing_open = await self.alerts.list_open_for_rule(rule.id)
        if existing_open:
            return None

        metric, comparator, threshold = rule.condition["metric"], rule.condition["comparator"], rule.condition["threshold"]
        message = f"{metric} {comparator} {threshold} tripped: observed {observed_value}"
        return await self.alerts.trigger_alert(
            rule.workspace_id, category=rule.category, severity=rule.severity, message=message,
            alert_rule_id=rule.id, context={"metric": metric, "observed_value": observed_value, "threshold": threshold},
        )

    async def evaluate_active_rules(self, workspace_id: str, observed_values: dict[str, float]) -> list[AlertModel]:
        """`observed_values` maps metric key -> genuinely observed value
        (pulled by the caller from `ObservabilityMonitoringService` or
        `MetricScorer` aggregates); rules whose metric isn't present in
        the map are silently skipped rather than evaluated against a
        fabricated value."""
        rules = await self.repos.alert_rules.list_active_for_workspace(workspace_id)
        triggered = []
        for rule in rules:
            metric = rule.condition.get("metric")
            if metric not in observed_values:
                continue
            alert = await self.evaluate_rule(rule, observed_values[metric])
            if alert is not None:
                triggered.append(alert)
        return triggered
