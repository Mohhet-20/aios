from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import DashboardNotFoundError, SavedViewNotFoundError
from analytics_platform.dashboards.dashboard_service import DashboardService
from analytics_platform.dashboards.saved_view_service import SavedViewService

TENANT = "saved-view-tenant"


@pytest.mark.asyncio
async def test_create_saved_view_requires_existing_dashboard(repos):
    service = SavedViewService(repos)
    with pytest.raises(DashboardNotFoundError):
        await service.create_saved_view(TENANT, "not-a-real-id", name="My View")


@pytest.mark.asyncio
async def test_create_and_list_saved_views(repos):
    dashboards = DashboardService(repos)
    dashboard = await dashboards.create_dashboard(TENANT, name="Sales")
    views = SavedViewService(repos)

    view = await views.create_saved_view(TENANT, dashboard.id, name="This Quarter", owner_id="user-1", filters={"quarter": "Q3"})
    listed = await views.list_for_dashboard(TENANT, dashboard.id)
    assert len(listed) == 1
    assert listed[0].id == view.id
    assert listed[0].filters == {"quarter": "Q3"}


@pytest.mark.asyncio
async def test_delete_saved_view(repos):
    dashboards = DashboardService(repos)
    dashboard = await dashboards.create_dashboard(TENANT, name="Sales")
    views = SavedViewService(repos)
    view = await views.create_saved_view(TENANT, dashboard.id, name="Temp View")

    await views.delete_saved_view(TENANT, dashboard.id, view.id)
    assert await views.list_for_dashboard(TENANT, dashboard.id) == []


@pytest.mark.asyncio
async def test_get_saved_view_wrong_dashboard_raises(repos):
    dashboards = DashboardService(repos)
    dashboard_a = await dashboards.create_dashboard(TENANT, name="A")
    dashboard_b = await dashboards.create_dashboard(TENANT, name="B")
    views = SavedViewService(repos)
    view = await views.create_saved_view(TENANT, dashboard_a.id, name="A's View")

    with pytest.raises(SavedViewNotFoundError):
        await views.get_or_404(TENANT, dashboard_b.id, view.id)
