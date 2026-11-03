"""Alert lifecycle operations that don't need cross-connection
dedup locking — acknowledge/resolve/suppress/unsuppress each act on a
single already-identified alert row, guarded by the `Alert` domain
entity's transition map."""
from __future__ import annotations

from datetime import datetime

from observability_platform.domain.entities import Alert as AlertEntity
from observability_platform.domain.enums import AlertStatus
from observability_platform.models.alerts import AlertModel
from observability_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: AlertModel) -> AlertEntity:
    return AlertEntity(
        id=model.id, status=AlertStatus(model.status), acknowledged_at=model.acknowledged_at,
        resolved_at=model.resolved_at, suppressed_until=model.suppressed_until,
    )


def _apply(model: AlertModel, entity: AlertEntity) -> AlertModel:
    model.status = entity.status.value
    model.acknowledged_at = entity.acknowledged_at
    model.resolved_at = entity.resolved_at
    model.suppressed_until = entity.suppressed_until
    return model


class AlertSuppressionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def acknowledge(self, tenant_id: str, alert_id: str, *, by: str | None = None) -> AlertModel:
        alert = await self.repos.alerts.get_or_404(alert_id)
        entity = _to_entity(alert)
        entity.acknowledge()
        alert = _apply(alert, entity)
        alert.acknowledged_by = by
        return await self.repos.alerts.update(alert)

    async def resolve(self, tenant_id: str, alert_id: str) -> AlertModel:
        alert = await self.repos.alerts.get_or_404(alert_id)
        entity = _to_entity(alert)
        entity.resolve()
        alert = _apply(alert, entity)
        return await self.repos.alerts.update(alert)

    async def suppress(self, tenant_id: str, alert_id: str, until: datetime) -> AlertModel:
        alert = await self.repos.alerts.get_or_404(alert_id)
        entity = _to_entity(alert)
        entity.suppress(until)
        alert = _apply(alert, entity)
        return await self.repos.alerts.update(alert)

    async def unsuppress(self, tenant_id: str, alert_id: str) -> AlertModel:
        alert = await self.repos.alerts.get_or_404(alert_id)
        entity = _to_entity(alert)
        entity.unsuppress()
        alert = _apply(alert, entity)
        return await self.repos.alerts.update(alert)
