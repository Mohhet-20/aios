from __future__ import annotations

import pytest

from observability_platform.core.exceptions import ValidationError
from observability_platform.dashboards.dashboard_service import DashboardService
from observability_platform.health.healthcheck_service import HealthCheckService
from observability_platform.incidents.incident_service import IncidentService
from observability_platform.models.components import ComponentModel


@pytest.mark.asyncio
async def test_create_dashboard_rejects_unknown_type(repos):
    svc = DashboardService(repos)
    with pytest.raises(ValidationError):
        await svc.create_dashboard("t1", name="Bad", dashboard_type="not-a-type")


@pytest.mark.asyncio
async def test_create_and_list_dashboards(repos):
    svc = DashboardService(repos)
    await svc.create_dashboard("t1", name="Exec Overview", dashboard_type="executive", is_default=True)
    await svc.create_dashboard("t1", name="Ops Board", dashboard_type="operations")

    all_dashboards = await svc.list_dashboards("t1")
    assert len(all_dashboards) == 2
    exec_only = await svc.list_dashboards("t1", dashboard_type="executive")
    assert len(exec_only) == 1


@pytest.mark.asyncio
async def test_render_executive_dashboard_pulls_live_data(repos):
    component = await repos.components.add(ComponentModel(tenant_id="t1", name="api", component_type="api_gateway"))
    health_svc = HealthCheckService(repos)
    await health_svc.record_result("t1", component.id, status="healthy")

    incident_svc = IncidentService(repos)
    await incident_svc.create_incident("t1", title="Something broke", severity="sev2")

    dash_svc = DashboardService(repos)
    dashboard = await dash_svc.create_dashboard("t1", name="Exec", dashboard_type="executive")
    rendered = await dash_svc.render("t1", dashboard.id)

    assert rendered["dashboard_type"] == "executive"
    assert rendered["widgets"]["system_health"]["overall_status"] == "healthy"
    assert rendered["widgets"]["incidents_by_severity"].get("sev2") == 1


@pytest.mark.asyncio
async def test_render_incident_dashboard_lists_open_incidents(repos):
    incident_svc = IncidentService(repos)
    open_inc = await incident_svc.create_incident("t1", title="Open one", severity="sev1")
    closed_inc = await incident_svc.create_incident("t1", title="Closed one", severity="sev4")
    await incident_svc.resolve("t1", closed_inc.id)
    await incident_svc.close("t1", closed_inc.id)

    dash_svc = DashboardService(repos)
    dashboard = await dash_svc.create_dashboard("t1", name="Incidents", dashboard_type="incident")
    rendered = await dash_svc.render("t1", dashboard.id)

    open_ids = {i["id"] for i in rendered["widgets"]["open_incidents"]}
    assert open_inc.id in open_ids
    assert closed_inc.id not in open_ids


@pytest.mark.asyncio
async def test_update_widgets_persists(repos):
    svc = DashboardService(repos)
    dashboard = await svc.create_dashboard("t1", name="Custom", dashboard_type="operations")
    updated = await svc.update_widgets("t1", dashboard.id, [{"type": "alert_count"}])
    assert updated.widgets == [{"type": "alert_count"}]


@pytest.mark.asyncio
async def test_render_every_dashboard_type_does_not_error(repos):
    """One test per dashboard type would be repetitive boilerplate —
    this loop exercises all ten renderers against an (mostly) empty
    tenant to catch any renderer that crashes on empty data, which is
    the most common real-world case for a freshly onboarded tenant."""
    from observability_platform.domain.enums import DashboardType

    dash_svc = DashboardService(repos)
    for dtype in DashboardType:
        dashboard = await dash_svc.create_dashboard("t1", name=f"dash-{dtype.value}", dashboard_type=dtype.value)
        rendered = await dash_svc.render("t1", dashboard.id)
        assert rendered["dashboard_type"] == dtype.value
        assert "widgets" in rendered
