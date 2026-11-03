from __future__ import annotations

import pytest

from observability_platform.core.exceptions import IncidentAlreadyClosedError, IncidentError, InvalidTransitionError
from observability_platform.incidents.incident_service import IncidentService
from observability_platform.incidents.postmortem_service import PostmortemService


@pytest.mark.asyncio
async def test_incident_full_lifecycle_with_timeline(repos):
    svc = IncidentService(repos)
    incident = await svc.create_incident("t1", title="API down", severity="sev1", created_by="alice")
    assert incident.status == "open"

    await svc.acknowledge("t1", incident.id, by="bob")
    await svc.mark_identified("t1", incident.id, root_cause="bad deploy", by="bob")
    await svc.mark_monitoring("t1", incident.id, by="bob")
    resolved = await svc.resolve("t1", incident.id, resolution_notes="rolled back", by="bob")
    assert resolved.status == "resolved"
    closed = await svc.close("t1", incident.id, by="bob")
    assert closed.status == "closed"

    timeline = await svc.timeline.list_timeline("t1", incident.id)
    event_types = [e.event_type for e in timeline]
    assert event_types == ["created", "acknowledged", "identified", "monitoring", "resolved", "closed"]


@pytest.mark.asyncio
async def test_incident_illegal_transition_raises(repos):
    svc = IncidentService(repos)
    incident = await svc.create_incident("t1", title="Minor blip", severity="sev4")
    with pytest.raises(InvalidTransitionError):
        await svc.mark_monitoring("t1", incident.id)  # can't skip straight from open


@pytest.mark.asyncio
async def test_incident_double_close_raises(repos):
    svc = IncidentService(repos)
    incident = await svc.create_incident("t1", title="Something broke")
    await svc.resolve("t1", incident.id)
    await svc.close("t1", incident.id)
    with pytest.raises(IncidentAlreadyClosedError):
        await svc.close("t1", incident.id)


@pytest.mark.asyncio
async def test_incident_reopen_on_regression(repos):
    svc = IncidentService(repos)
    incident = await svc.create_incident("t1", title="Flaky endpoint")
    await svc.resolve("t1", incident.id)
    reopened = await svc.reopen("t1", incident.id, reason="regression detected")
    assert reopened.status == "investigating"


@pytest.mark.asyncio
async def test_assign_incident_records_timeline_event(repos):
    svc = IncidentService(repos)
    incident = await svc.create_incident("t1", title="Needs an owner")
    assigned = await svc.assign("t1", incident.id, "carol", by="alice")
    assert assigned.assigned_to == "carol"
    timeline = await svc.timeline.list_timeline("t1", incident.id)
    assert any(e.event_type == "assigned" for e in timeline)


@pytest.mark.asyncio
async def test_postmortem_requires_resolved_or_closed_incident(repos):
    svc = IncidentService(repos)
    incident = await svc.create_incident("t1", title="Still open")
    pm_svc = PostmortemService(repos)
    with pytest.raises(IncidentError):
        await pm_svc.create_or_update("t1", incident.id, summary="too early")


@pytest.mark.asyncio
async def test_postmortem_create_update_and_publish(repos):
    inc_svc = IncidentService(repos)
    incident = await inc_svc.create_incident("t1", title="Outage")
    await inc_svc.resolve("t1", incident.id)

    pm_svc = PostmortemService(repos)
    pm = await pm_svc.create_or_update(
        "t1", incident.id, summary="draft summary", action_items=[{"owner": "bob", "task": "add alert"}]
    )
    assert pm.published_at is None

    updated = await pm_svc.create_or_update("t1", incident.id, summary="final summary")
    assert updated.id == pm.id
    assert updated.summary == "final summary"

    published = await pm_svc.publish("t1", incident.id)
    assert published.published_at is not None
