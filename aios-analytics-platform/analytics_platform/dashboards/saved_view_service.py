"""Self-service analytics: saved views are a named filter/layout
preset a user can return to on a given dashboard, without needing an
engineer to build them a new one -- this is the piece of the platform
that lets organizations build (and re-use) custom dashboard slices
without engineering changes."""
from __future__ import annotations

from analytics_platform.core.exceptions import DashboardNotFoundError, NotFoundError, SavedViewNotFoundError
from analytics_platform.models.dashboards import SavedViewModel
from analytics_platform.repositories.registry import RepositoryRegistry


class SavedViewService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def _assert_dashboard_exists(self, tenant_id: str, dashboard_id: str) -> None:
        try:
            dashboard = await self.repos.dashboards.get_or_404(dashboard_id)
        except NotFoundError as exc:
            raise DashboardNotFoundError(f"Dashboard '{dashboard_id}' not found for tenant '{tenant_id}'") from exc
        if dashboard.tenant_id != tenant_id:
            raise DashboardNotFoundError(f"Dashboard '{dashboard_id}' not found for tenant '{tenant_id}'")

    async def create_saved_view(
        self, tenant_id: str, dashboard_id: str, *, name: str, owner_id: str | None = None, filters: dict | None = None,
    ) -> SavedViewModel:
        await self._assert_dashboard_exists(tenant_id, dashboard_id)
        view = SavedViewModel(tenant_id=tenant_id, dashboard_id=dashboard_id, owner_id=owner_id, name=name, filters=filters or {})
        return await self.repos.saved_views.add(view)

    async def list_for_dashboard(self, tenant_id: str, dashboard_id: str) -> list[SavedViewModel]:
        return await self.repos.saved_views.list_for_dashboard(tenant_id, dashboard_id)

    async def get_or_404(self, tenant_id: str, dashboard_id: str, view_id: str) -> SavedViewModel:
        view = await self.repos.saved_views.get_or_404(view_id)
        if view.tenant_id != tenant_id or view.dashboard_id != dashboard_id:
            raise SavedViewNotFoundError(f"Saved view '{view_id}' not found on dashboard '{dashboard_id}'")
        return view

    async def delete_saved_view(self, tenant_id: str, dashboard_id: str, view_id: str) -> None:
        view = await self.get_or_404(tenant_id, dashboard_id, view_id)
        await self.repos.saved_views.delete(view, hard=True)
