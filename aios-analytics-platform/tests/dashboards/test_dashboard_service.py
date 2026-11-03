from __future__ import annotations

import pytest

from analytics_platform.config.settings import Settings
from analytics_platform.core.exceptions import (
    DashboardNotFoundError,
    InvalidTransitionError,
    TooManyWidgetsError,
    UnsupportedVisualizationTypeError,
    ValidationError,
    WidgetNotFoundError,
)
from analytics_platform.dashboards.dashboard_service import DashboardService

TENANT = "dash-tenant"


@pytest.mark.asyncio
async def test_create_dashboard_rejects_bad_visibility(repos):
    service = DashboardService(repos)
    with pytest.raises(ValidationError):
        await service.create_dashboard(TENANT, name="Bad", visibility="not_a_visibility")


@pytest.mark.asyncio
async def test_create_dashboard_defaults_to_draft(repos):
    service = DashboardService(repos)
    dashboard = await service.create_dashboard(TENANT, name="Exec Overview")
    assert dashboard.status == "draft"
    assert dashboard.visibility == "private"


@pytest.mark.asyncio
async def test_publish_archive_republish_lifecycle(repos):
    service = DashboardService(repos)
    dashboard = await service.create_dashboard(TENANT, name="Ops Overview")

    published = await service.publish(TENANT, dashboard.id)
    assert published.status == "published"

    archived = await service.archive(TENANT, dashboard.id)
    assert archived.status == "archived"

    republished = await service.republish(TENANT, dashboard.id)
    assert republished.status == "published"


@pytest.mark.asyncio
async def test_publish_twice_raises(repos):
    service = DashboardService(repos)
    dashboard = await service.create_dashboard(TENANT, name="Twice")
    await service.publish(TENANT, dashboard.id)
    with pytest.raises(InvalidTransitionError):
        await service.publish(TENANT, dashboard.id)


@pytest.mark.asyncio
async def test_not_found_for_other_tenant(repos):
    service = DashboardService(repos)
    dashboard = await service.create_dashboard(TENANT, name="Private")
    with pytest.raises(DashboardNotFoundError):
        await service.get_or_404("other-tenant", dashboard.id)


@pytest.mark.asyncio
async def test_update_layout(repos):
    service = DashboardService(repos)
    dashboard = await service.create_dashboard(TENANT, name="Layout Test")
    updated = await service.update_layout(TENANT, dashboard.id, {"columns": 3})
    assert updated.layout == {"columns": 3}


@pytest.mark.asyncio
async def test_add_widget_rejects_bad_visualization_type(repos):
    service = DashboardService(repos)
    dashboard = await service.create_dashboard(TENANT, name="Widgets")
    with pytest.raises(UnsupportedVisualizationTypeError):
        await service.add_widget(TENANT, dashboard.id, visualization_type="pie_chart_3000", title="Bad")


@pytest.mark.asyncio
async def test_add_and_list_and_remove_widget(repos):
    service = DashboardService(repos)
    dashboard = await service.create_dashboard(TENANT, name="Widgets")
    widget = await service.add_widget(
        TENANT, dashboard.id, visualization_type="line_chart", title="Revenue Over Time",
        query_config={"metric_key": "revenue.total"},
    )
    widgets = await service.list_widgets(TENANT, dashboard.id)
    assert len(widgets) == 1
    assert widgets[0].id == widget.id

    await service.remove_widget(TENANT, dashboard.id, widget.id)
    assert await service.list_widgets(TENANT, dashboard.id) == []


@pytest.mark.asyncio
async def test_get_widget_wrong_dashboard_raises(repos):
    service = DashboardService(repos)
    dashboard_a = await service.create_dashboard(TENANT, name="A")
    dashboard_b = await service.create_dashboard(TENANT, name="B")
    widget = await service.add_widget(TENANT, dashboard_a.id, visualization_type="table", title="Table")
    with pytest.raises(WidgetNotFoundError):
        await service.get_widget_or_404(TENANT, dashboard_b.id, widget.id)


@pytest.mark.asyncio
async def test_add_widget_enforces_max_widgets(repos):
    settings = Settings(dashboard_max_widgets=2)
    service = DashboardService(repos, settings=settings)
    dashboard = await service.create_dashboard(TENANT, name="Capped")
    await service.add_widget(TENANT, dashboard.id, visualization_type="scorecard", title="One")
    await service.add_widget(TENANT, dashboard.id, visualization_type="scorecard", title="Two")
    with pytest.raises(TooManyWidgetsError):
        await service.add_widget(TENANT, dashboard.id, visualization_type="scorecard", title="Three")
