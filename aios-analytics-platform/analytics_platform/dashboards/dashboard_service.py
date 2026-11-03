"""Visualization & Dashboard Platform: dashboards guarded through
draft -> published <-> archived, and their widgets -- one row per
widget across all eleven visualization types the prompt specifies
(free-form `query_config` JSON per widget, so no per-viz-type table is
needed, the same generic-row precedent used throughout this platform).
`dashboard_max_widgets` (config/settings.py) caps widget count per
dashboard so a single dashboard can't silently grow into something
nothing can render."""
from __future__ import annotations

from analytics_platform.config.settings import Settings, get_settings
from analytics_platform.core.exceptions import (
    DashboardNotFoundError,
    InvalidTransitionError,
    TooManyWidgetsError,
    UnsupportedVisualizationTypeError,
    ValidationError,
    WidgetNotFoundError,
)
from analytics_platform.domain.entities import Dashboard
from analytics_platform.domain.enums import DashboardStatus, DashboardVisibility, VisualizationType
from analytics_platform.models.dashboards import DashboardModel, DashboardWidgetModel
from analytics_platform.repositories.registry import RepositoryRegistry


class DashboardService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid_visibility(self, visibility: str) -> None:
        if visibility not in {v.value for v in DashboardVisibility}:
            raise ValidationError(f"'{visibility}' is not a recognized dashboard visibility")

    async def create_dashboard(
        self, tenant_id: str, *, name: str, description: str | None = None, owner_id: str | None = None,
        visibility: str = "private", layout: dict | None = None,
    ) -> DashboardModel:
        self._assert_valid_visibility(visibility)
        dashboard = DashboardModel(
            tenant_id=tenant_id, name=name, description=description, owner_id=owner_id,
            visibility=visibility, layout=layout or {}, status=DashboardStatus.DRAFT.value,
        )
        return await self.repos.dashboards.add(dashboard)

    async def get_or_404(self, tenant_id: str, dashboard_id: str) -> DashboardModel:
        dashboard = await self.repos.dashboards.get_or_404(dashboard_id)
        if dashboard.tenant_id != tenant_id:
            raise DashboardNotFoundError(f"Dashboard '{dashboard_id}' not found for tenant '{tenant_id}'")
        return dashboard

    async def list_for_tenant(self, tenant_id: str, *, status: str | None = None) -> list[DashboardModel]:
        return await self.repos.dashboards.list_for_tenant(tenant_id, status=status)

    async def update_layout(self, tenant_id: str, dashboard_id: str, layout: dict) -> DashboardModel:
        dashboard = await self.get_or_404(tenant_id, dashboard_id)
        dashboard.layout = layout
        return await self.repos.dashboards.update(dashboard)

    async def _apply_transition(self, tenant_id: str, dashboard_id: str, transition_name: str) -> DashboardModel:
        dashboard = await self.get_or_404(tenant_id, dashboard_id)
        entity = Dashboard(id=dashboard.id, status=DashboardStatus(dashboard.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        dashboard.status = entity.status.value
        return await self.repos.dashboards.update(dashboard)

    async def publish(self, tenant_id: str, dashboard_id: str) -> DashboardModel:
        return await self._apply_transition(tenant_id, dashboard_id, "publish")

    async def archive(self, tenant_id: str, dashboard_id: str) -> DashboardModel:
        return await self._apply_transition(tenant_id, dashboard_id, "archive")

    async def republish(self, tenant_id: str, dashboard_id: str) -> DashboardModel:
        return await self._apply_transition(tenant_id, dashboard_id, "republish")

    async def add_widget(
        self, tenant_id: str, dashboard_id: str, *, visualization_type: str, title: str,
        query_config: dict | None = None, position: dict | None = None,
    ) -> DashboardWidgetModel:
        await self.get_or_404(tenant_id, dashboard_id)
        if visualization_type not in {t.value for t in VisualizationType}:
            raise UnsupportedVisualizationTypeError(f"'{visualization_type}' is not a recognized visualization type")
        current_count = await self.repos.dashboard_widgets.count_for_dashboard(tenant_id, dashboard_id)
        if current_count >= self.settings.dashboard_max_widgets:
            raise TooManyWidgetsError(
                f"dashboard '{dashboard_id}' already has {current_count} widgets, "
                f"the max is {self.settings.dashboard_max_widgets}"
            )
        widget = DashboardWidgetModel(
            tenant_id=tenant_id, dashboard_id=dashboard_id, visualization_type=visualization_type,
            title=title, query_config=query_config or {}, position=position or {},
        )
        return await self.repos.dashboard_widgets.add(widget)

    async def list_widgets(self, tenant_id: str, dashboard_id: str) -> list[DashboardWidgetModel]:
        return await self.repos.dashboard_widgets.list_for_dashboard(tenant_id, dashboard_id)

    async def get_widget_or_404(self, tenant_id: str, dashboard_id: str, widget_id: str) -> DashboardWidgetModel:
        widget = await self.repos.dashboard_widgets.get_or_404(widget_id)
        if widget.tenant_id != tenant_id or widget.dashboard_id != dashboard_id:
            raise WidgetNotFoundError(f"Widget '{widget_id}' not found on dashboard '{dashboard_id}'")
        return widget

    async def remove_widget(self, tenant_id: str, dashboard_id: str, widget_id: str) -> None:
        widget = await self.get_widget_or_404(tenant_id, dashboard_id, widget_id)
        await self.repos.dashboard_widgets.delete(widget, hard=True)
