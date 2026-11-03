import pytest


@pytest.mark.asyncio
async def test_evaluate_rule_triggers_when_condition_trips(evaluator, rule_service, workspace):
    rule = await rule_service.create_rule(
        workspace.id, name="High Latency", category="latency", severity="warning",
        condition={"metric": "latency_ms", "comparator": "gt", "threshold": 1000},
    )
    alert = await evaluator.evaluate_rule(rule, 1500)
    assert alert is not None
    assert alert.category == "latency"
    assert alert.context["observed_value"] == 1500


@pytest.mark.asyncio
async def test_evaluate_rule_does_not_trigger_when_condition_not_met(evaluator, rule_service, workspace):
    rule = await rule_service.create_rule(
        workspace.id, name="High Latency", category="latency", severity="warning",
        condition={"metric": "latency_ms", "comparator": "gt", "threshold": 1000},
    )
    alert = await evaluator.evaluate_rule(rule, 500)
    assert alert is None


@pytest.mark.asyncio
async def test_evaluate_rule_skips_inactive_rules(evaluator, rule_service, workspace):
    rule = await rule_service.create_rule(
        workspace.id, name="High Latency", category="latency", severity="warning",
        condition={"metric": "latency_ms", "comparator": "gt", "threshold": 1000},
    )
    await rule_service.set_active(rule.id, False)
    rule = await rule_service.get_rule(rule.id)
    alert = await evaluator.evaluate_rule(rule, 5000)
    assert alert is None


@pytest.mark.asyncio
async def test_evaluate_rule_deduplicates_open_alerts(evaluator, rule_service, workspace):
    rule = await rule_service.create_rule(
        workspace.id, name="High Latency", category="latency", severity="warning",
        condition={"metric": "latency_ms", "comparator": "gt", "threshold": 1000},
    )
    first = await evaluator.evaluate_rule(rule, 1500)
    second = await evaluator.evaluate_rule(rule, 2000)
    assert first is not None
    assert second is None

    open_alerts = await evaluator.alerts.list_open_for_rule(rule.id)
    assert len(open_alerts) == 1


@pytest.mark.asyncio
async def test_evaluate_rule_retriggers_after_resolution(evaluator, rule_service, workspace):
    rule = await rule_service.create_rule(
        workspace.id, name="High Latency", category="latency", severity="warning",
        condition={"metric": "latency_ms", "comparator": "gt", "threshold": 1000},
    )
    first = await evaluator.evaluate_rule(rule, 1500)
    await evaluator.alerts.resolve(first.id, by="u1")
    second = await evaluator.evaluate_rule(rule, 2000)
    assert second is not None
    assert second.id != first.id


@pytest.mark.asyncio
async def test_evaluate_active_rules_skips_metrics_without_observed_values(evaluator, rule_service, workspace):
    await rule_service.create_rule(
        workspace.id, name="High Latency", category="latency", severity="warning",
        condition={"metric": "latency_ms", "comparator": "gt", "threshold": 1000},
    )
    await rule_service.create_rule(
        workspace.id, name="High Cost", category="cost", severity="critical",
        condition={"metric": "cost", "comparator": "gt", "threshold": 5.0},
    )
    triggered = await evaluator.evaluate_active_rules(workspace.id, {"latency_ms": 5000})
    assert len(triggered) == 1
    assert triggered[0].category == "latency"
