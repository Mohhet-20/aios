from __future__ import annotations

from datetime import timedelta

import pytest

from observability_platform.alerts.escalation_service import AlertEscalationService
from observability_platform.alerts.evaluation_service import AlertEvaluationService, evaluate_anomaly, evaluate_threshold
from observability_platform.alerts.maintenance_window_service import MaintenanceWindowService
from observability_platform.alerts.rule_service import AlertRuleService
from observability_platform.alerts.suppression_service import AlertSuppressionService
from observability_platform.core.exceptions import AlertAlreadyResolvedError, AlertRuleError, ValidationError
from observability_platform.database.base import utcnow
from observability_platform.metrics.ingest_service import MetricIngestService
from observability_platform.models.alerts import EscalationPolicyModel, NotificationChannelModel
from observability_platform.models.components import ComponentModel


def test_evaluate_threshold_operators():
    assert evaluate_threshold(95, {"operator": "gt", "value": 90}) is True
    assert evaluate_threshold(85, {"operator": "gt", "value": 90}) is False
    assert evaluate_threshold(90, {"operator": "gte", "value": 90}) is True
    with pytest.raises(ValidationError):
        evaluate_threshold(1, {"operator": "nope", "value": 1})


def test_evaluate_anomaly_detects_deviation():
    baseline = [10.0, 11.0, 9.0, 10.5, 9.5]
    assert evaluate_anomaly(50.0, baseline, {"deviation_multiplier": 3.0}) is True
    assert evaluate_anomaly(10.2, baseline, {"deviation_multiplier": 3.0}) is False
    assert evaluate_anomaly(50.0, [1.0], {}) is False  # not enough history


@pytest.mark.asyncio
async def test_rule_service_rejects_bad_input(repos):
    svc = AlertRuleService(repos)
    with pytest.raises(ValidationError):
        await svc.create_rule("t1", name="x", alert_type="not-a-type", condition={"operator": "gt", "value": 1})
    with pytest.raises(AlertRuleError):
        await svc.create_rule("t1", name="x", alert_type="threshold", condition={})


@pytest.mark.asyncio
async def test_evaluate_rule_fires_and_auto_resolves(repos):
    rule_svc = AlertRuleService(repos)
    metric_svc = MetricIngestService(repos)
    eval_svc = AlertEvaluationService(repos)

    rule = await rule_svc.create_rule(
        "t1", name="high-cpu", alert_type="threshold", metric_name="alert_cpu_usage",
        condition={"operator": "gt", "value": 90},
    )
    await metric_svc.ingest("t1", name="alert_cpu_usage", metric_type="gauge", value=95.0)
    alert = await eval_svc.evaluate_rule("t1", rule)
    assert alert is not None
    assert alert.status == "firing"

    # Re-evaluating while still breached should update, not duplicate.
    await metric_svc.ingest("t1", name="alert_cpu_usage", metric_type="gauge", value=96.0)
    alert2 = await eval_svc.evaluate_rule("t1", rule)
    assert alert2.id == alert.id
    active = await repos.alerts.list_by_status("t1", "firing")
    assert len(active) == 1

    # Healing (value drops below threshold) should auto-resolve.
    await metric_svc.ingest("t1", name="alert_cpu_usage", metric_type="gauge", value=10.0)
    resolved = await eval_svc.evaluate_rule("t1", rule)
    assert resolved is not None
    assert resolved.status == "resolved"


@pytest.mark.asyncio
async def test_maintenance_window_suppresses_firing(repos):
    component = await repos.components.add(ComponentModel(tenant_id="t1", name="db", component_type="database"))
    mw_svc = MaintenanceWindowService(repos)
    now = utcnow()
    await mw_svc.schedule(
        "t1", name="db upgrade", starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=30),
        component_id=component.id, suppress_alerts=True,
    )

    rule_svc = AlertRuleService(repos)
    metric_svc = MetricIngestService(repos)
    eval_svc = AlertEvaluationService(repos)
    rule = await rule_svc.create_rule(
        "t1", name="db-down", alert_type="availability", metric_name="db_up",
        condition={"operator": "lt", "value": 1}, component_id=component.id,
    )
    await metric_svc.ingest("t1", name="db_up", metric_type="gauge", value=0.0, component_id=component.id)
    alert = await eval_svc.evaluate_rule("t1", rule, component_id=component.id)
    assert alert is None  # suppressed by the active maintenance window


@pytest.mark.asyncio
async def test_suppression_service_lifecycle(repos):
    rule_svc = AlertRuleService(repos)
    metric_svc = MetricIngestService(repos)
    eval_svc = AlertEvaluationService(repos)
    rule = await rule_svc.create_rule(
        "t1", name="high-lat", alert_type="latency", metric_name="alert_latency_ms", condition={"operator": "gt", "value": 100}
    )
    await metric_svc.ingest("t1", name="alert_latency_ms", metric_type="gauge", value=500.0)
    alert = await eval_svc.evaluate_rule("t1", rule)

    supp = AlertSuppressionService(repos)
    acked = await supp.acknowledge("t1", alert.id, by="oncall-user")
    assert acked.status == "acknowledged"
    assert acked.acknowledged_by == "oncall-user"

    resolved = await supp.resolve("t1", alert.id)
    assert resolved.status == "resolved"

    with pytest.raises(AlertAlreadyResolvedError):
        await supp.resolve("t1", alert.id)


@pytest.mark.asyncio
async def test_escalation_walks_policy_levels_and_notifies(repos):
    channel = await repos.notification_channels.add(
        NotificationChannelModel(tenant_id="t1", name="oncall", channel_type="pagerduty", config={})
    )
    policy = await repos.escalation_policies.add(
        EscalationPolicyModel(
            tenant_id="t1", name="default",
            levels=[{"level": 1, "delay_minutes": 0, "targets": [channel.id]}, {"level": 2, "delay_minutes": 15, "targets": [channel.id]}],
        )
    )
    rule_svc = AlertRuleService(repos)
    rule = await rule_svc.create_rule(
        "t1", name="critical-rule", alert_type="threshold", metric_name="err_rate",
        condition={"operator": "gt", "value": 0.5}, escalation_policy_id=policy.id,
    )
    metric_svc = MetricIngestService(repos)
    eval_svc = AlertEvaluationService(repos)
    await metric_svc.ingest("t1", name="err_rate", metric_type="gauge", value=0.9)
    alert = await eval_svc.evaluate_rule("t1", rule)

    esc_svc = AlertEscalationService(repos)
    level1 = await esc_svc.escalate("t1", alert.id)
    assert len(level1) == 1
    assert level1[0].level == 1

    level2 = await esc_svc.escalate("t1", alert.id)
    assert level2[0].level == 2

    level3 = await esc_svc.escalate("t1", alert.id)  # past the top of the policy
    assert level3 == []

    notifications = await repos.alert_notifications.list_for_alert("t1", alert.id)
    assert len(notifications) == 2
    assert all(n.status == "sent" for n in notifications)
