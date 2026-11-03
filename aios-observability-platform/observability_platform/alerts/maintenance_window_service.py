"""Maintenance windows: scheduled/active/completed/cancelled lifecycle
(guarded via the `MaintenanceWindow` domain entity) plus the query
`AlertEvaluationService` uses before firing a new alert — a component
inside an active, alert-suppressing maintenance window should not page
anyone."""
from __future__ import annotations

from datetime import datetime

from observability_platform.core.exceptions import MaintenanceWindowError
from observability_platform.database.base import utcnow
from observability_platform.domain.entities import MaintenanceWindow as MaintenanceWindowEntity
from observability_platform.domain.enums import MaintenanceWindowStatus
from observability_platform.models.alerts import MaintenanceWindowModel
from observability_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: MaintenanceWindowModel) -> MaintenanceWindowEntity:
    return MaintenanceWindowEntity(id=model.id, status=MaintenanceWindowStatus(model.status))


class MaintenanceWindowService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def schedule(
        self,
        tenant_id: str,
        *,
        name: str,
        starts_at: datetime,
        ends_at: datetime,
        component_id: str | None = None,
        suppress_alerts: bool = True,
        reason: str | None = None,
    ) -> MaintenanceWindowModel:
        if ends_at <= starts_at:
            raise MaintenanceWindowError("Maintenance window end time must be after start time")
        window = MaintenanceWindowModel(
            tenant_id=tenant_id, name=name, starts_at=starts_at, ends_at=ends_at,
            component_id=component_id, suppress_alerts=suppress_alerts, reason=reason,
        )
        return await self.repos.maintenance_windows.add(window)

    async def activate(self, tenant_id: str, window_id: str) -> MaintenanceWindowModel:
        window = await self.repos.maintenance_windows.get_or_404(window_id)
        entity = _to_entity(window)
        entity.activate()
        window.status = entity.status.value
        return await self.repos.maintenance_windows.update(window)

    async def complete(self, tenant_id: str, window_id: str) -> MaintenanceWindowModel:
        window = await self.repos.maintenance_windows.get_or_404(window_id)
        entity = _to_entity(window)
        entity.complete()
        window.status = entity.status.value
        return await self.repos.maintenance_windows.update(window)

    async def cancel(self, tenant_id: str, window_id: str) -> MaintenanceWindowModel:
        window = await self.repos.maintenance_windows.get_or_404(window_id)
        entity = _to_entity(window)
        entity.cancel()
        window.status = entity.status.value
        return await self.repos.maintenance_windows.update(window)

    async def is_alert_suppressed(self, tenant_id: str, component_id: str, *, at: datetime | None = None) -> bool:
        windows = await self.repos.maintenance_windows.list_active_for_component(
            tenant_id, component_id, at=at or utcnow()
        )
        return any(w.suppress_alerts for w in windows)
