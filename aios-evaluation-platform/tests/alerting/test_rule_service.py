import pytest

from eval_platform.core.exceptions import AlertRuleError
from eval_platform.core.pagination import PaginationParams


@pytest.mark.asyncio
async def test_create_rule(rule_service, workspace):
    rule = await rule_service.create_rule(
        workspace.id, name="High Hallucination Rate", category="quality", severity="warning",
        condition={"metric": "hallucination_rate", "comparator": "gt", "threshold": 0.2},
    )
    assert rule.is_active is True
    assert rule.condition["threshold"] == 0.2


@pytest.mark.asyncio
async def test_create_rule_rejects_unknown_category(rule_service, workspace):
    with pytest.raises(AlertRuleError):
        await rule_service.create_rule(workspace.id, name="X", category="not_real", severity="warning", condition={"metric": "m", "comparator": "gt", "threshold": 1})


@pytest.mark.asyncio
async def test_create_rule_rejects_unknown_severity(rule_service, workspace):
    with pytest.raises(AlertRuleError):
        await rule_service.create_rule(workspace.id, name="X", category="cost", severity="not_real", condition={"metric": "m", "comparator": "gt", "threshold": 1})


@pytest.mark.asyncio
async def test_create_rule_rejects_missing_metric(rule_service, workspace):
    with pytest.raises(AlertRuleError):
        await rule_service.create_rule(workspace.id, name="X", category="cost", severity="warning", condition={"comparator": "gt", "threshold": 1})


@pytest.mark.asyncio
async def test_create_rule_rejects_bad_comparator(rule_service, workspace):
    with pytest.raises(AlertRuleError):
        await rule_service.create_rule(workspace.id, name="X", category="cost", severity="warning", condition={"metric": "m", "comparator": "bogus", "threshold": 1})


@pytest.mark.asyncio
async def test_create_rule_rejects_non_numeric_threshold(rule_service, workspace):
    with pytest.raises(AlertRuleError):
        await rule_service.create_rule(workspace.id, name="X", category="cost", severity="warning", condition={"metric": "m", "comparator": "gt", "threshold": "high"})


@pytest.mark.asyncio
async def test_create_rule_rejects_negative_window(rule_service, workspace):
    with pytest.raises(AlertRuleError):
        await rule_service.create_rule(workspace.id, name="X", category="cost", severity="warning", condition={"metric": "m", "comparator": "gt", "threshold": 1, "window_minutes": -5})


@pytest.mark.asyncio
async def test_update_rule_rejects_unknown_field(rule_service, workspace):
    rule = await rule_service.create_rule(workspace.id, name="X", category="cost", severity="warning", condition={"metric": "m", "comparator": "gt", "threshold": 1})
    with pytest.raises(AlertRuleError):
        await rule_service.update_rule(rule.id, category="quality")


@pytest.mark.asyncio
async def test_set_active_and_list_active(rule_service, workspace):
    rule = await rule_service.create_rule(workspace.id, name="X", category="cost", severity="warning", condition={"metric": "m", "comparator": "gt", "threshold": 1})
    active = await rule_service.list_active_rules(workspace.id)
    assert len(active) == 1

    await rule_service.set_active(rule.id, False)
    active = await rule_service.list_active_rules(workspace.id)
    assert len(active) == 0


@pytest.mark.asyncio
async def test_list_rules_paginated_and_delete(rule_service, workspace):
    rule = await rule_service.create_rule(workspace.id, name="X", category="cost", severity="warning", condition={"metric": "m", "comparator": "gt", "threshold": 1})
    page = await rule_service.list_rules(workspace.id, PaginationParams(page=1, page_size=10))
    assert page.total == 1
    await rule_service.delete_rule(rule.id)
    page = await rule_service.list_rules(workspace.id, PaginationParams(page=1, page_size=10))
    assert page.total == 0
