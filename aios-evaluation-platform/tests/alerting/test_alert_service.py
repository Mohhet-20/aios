import pytest

from eval_platform.core.exceptions import AlertRuleError, InvalidTransitionError


@pytest.mark.asyncio
async def test_trigger_alert(alert_service, workspace):
    alert = await alert_service.trigger_alert(workspace.id, category="cost", severity="critical", message="Cost spiked")
    assert alert.status == "open"


@pytest.mark.asyncio
async def test_trigger_alert_rejects_unknown_category(alert_service, workspace):
    with pytest.raises(AlertRuleError):
        await alert_service.trigger_alert(workspace.id, category="not_real", severity="critical", message="x")


@pytest.mark.asyncio
async def test_acknowledge_resolve_reopen_lifecycle(alert_service, workspace):
    alert = await alert_service.trigger_alert(workspace.id, category="failure", severity="warning", message="Failures rising")

    acknowledged = await alert_service.acknowledge(alert.id, by="u1")
    assert acknowledged.status == "acknowledged"
    assert acknowledged.acknowledged_by == "u1"

    resolved = await alert_service.resolve(acknowledged.id, by="u1")
    assert resolved.status == "resolved"
    assert resolved.resolved_by == "u1"


@pytest.mark.asyncio
async def test_cannot_resolve_directly_is_allowed_open_to_resolved(alert_service, workspace):
    alert = await alert_service.trigger_alert(workspace.id, category="failure", severity="warning", message="x")
    resolved = await alert_service.resolve(alert.id, by="u1")
    assert resolved.status == "resolved"


@pytest.mark.asyncio
async def test_cannot_transition_from_resolved(alert_service, workspace):
    alert = await alert_service.trigger_alert(workspace.id, category="failure", severity="warning", message="x")
    resolved = await alert_service.resolve(alert.id, by="u1")
    with pytest.raises(InvalidTransitionError):
        await alert_service.acknowledge(resolved.id, by="u1")


@pytest.mark.asyncio
async def test_reopen_from_acknowledged(alert_service, workspace):
    alert = await alert_service.trigger_alert(workspace.id, category="failure", severity="warning", message="x")
    await alert_service.acknowledge(alert.id, by="u1")
    reopened = await alert_service.reopen(alert.id)
    assert reopened.status == "open"
    assert reopened.acknowledged_by is None


@pytest.mark.asyncio
async def test_list_alerts_filters(alert_service, workspace):
    await alert_service.trigger_alert(workspace.id, category="cost", severity="warning", message="a")
    b = await alert_service.trigger_alert(workspace.id, category="failure", severity="critical", message="b")
    await alert_service.resolve(b.id, by="u1")

    open_alerts = await alert_service.list_alerts(workspace.id, status="open")
    assert len(open_alerts) == 1
    cost_alerts = await alert_service.list_alerts(workspace.id, category="cost")
    assert len(cost_alerts) == 1
