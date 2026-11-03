from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from observability_platform.models.alerts import (
    AlertEscalationModel,
    AlertModel,
    AlertNotificationModel,
    AlertRuleModel,
    EscalationPolicyModel,
    MaintenanceWindowModel,
    NotificationChannelModel,
)
from observability_platform.repositories.base import SQLAlchemyRepository


class AlertRuleRepository(SQLAlchemyRepository[AlertRuleModel]):
    model = AlertRuleModel

    async def list_enabled(self, tenant_id: str) -> list[AlertRuleModel]:
        stmt = select(AlertRuleModel).where(
            AlertRuleModel.tenant_id == tenant_id,
            AlertRuleModel.is_deleted.is_(False),
            AlertRuleModel.is_enabled.is_(True),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class AlertRepository(SQLAlchemyRepository[AlertModel]):
    model = AlertModel

    async def find_active_by_dedup_key(self, tenant_id: str, dedup_key: str) -> AlertModel | None:
        """Active means still firing/acknowledged — used to decide
        whether a new evaluation should update an existing alert
        in-place or open a brand new one."""
        stmt = select(AlertModel).where(
            AlertModel.tenant_id == tenant_id,
            AlertModel.dedup_key == dedup_key,
            AlertModel.status.in_(["firing", "acknowledged"]),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_status(self, tenant_id: str, status: str, *, limit: int = 200) -> list[AlertModel]:
        stmt = (
            select(AlertModel)
            .where(AlertModel.tenant_id == tenant_id, AlertModel.status == status)
            .order_by(AlertModel.fired_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_component(self, tenant_id: str, component_id: str, *, limit: int = 200) -> list[AlertModel]:
        stmt = (
            select(AlertModel)
            .where(AlertModel.tenant_id == tenant_id, AlertModel.component_id == component_id)
            .order_by(AlertModel.fired_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(AlertModel.status, func.count())
            .where(AlertModel.tenant_id == tenant_id)
            .group_by(AlertModel.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {status: count for status, count in rows}


class EscalationPolicyRepository(SQLAlchemyRepository[EscalationPolicyModel]):
    model = EscalationPolicyModel


class AlertEscalationRepository(SQLAlchemyRepository[AlertEscalationModel]):
    model = AlertEscalationModel

    async def list_for_alert(self, tenant_id: str, alert_id: str) -> list[AlertEscalationModel]:
        stmt = (
            select(AlertEscalationModel)
            .where(AlertEscalationModel.tenant_id == tenant_id, AlertEscalationModel.alert_id == alert_id)
            .order_by(AlertEscalationModel.level.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def highest_level_for_alert(self, tenant_id: str, alert_id: str) -> int:
        rows = await self.list_for_alert(tenant_id, alert_id)
        return max((r.level for r in rows), default=0)


class MaintenanceWindowRepository(SQLAlchemyRepository[MaintenanceWindowModel]):
    model = MaintenanceWindowModel

    async def list_active_for_component(self, tenant_id: str, component_id: str, *, at: datetime) -> list[MaintenanceWindowModel]:
        stmt = select(MaintenanceWindowModel).where(
            MaintenanceWindowModel.tenant_id == tenant_id,
            MaintenanceWindowModel.is_deleted.is_(False),
            MaintenanceWindowModel.component_id == component_id,
            MaintenanceWindowModel.status.in_(["scheduled", "active"]),
            MaintenanceWindowModel.starts_at <= at,
            MaintenanceWindowModel.ends_at >= at,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class NotificationChannelRepository(SQLAlchemyRepository[NotificationChannelModel]):
    model = NotificationChannelModel

    async def list_enabled(self, tenant_id: str) -> list[NotificationChannelModel]:
        stmt = select(NotificationChannelModel).where(
            NotificationChannelModel.tenant_id == tenant_id,
            NotificationChannelModel.is_deleted.is_(False),
            NotificationChannelModel.is_enabled.is_(True),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class AlertNotificationRepository(SQLAlchemyRepository[AlertNotificationModel]):
    model = AlertNotificationModel

    async def list_for_alert(self, tenant_id: str, alert_id: str) -> list[AlertNotificationModel]:
        stmt = select(AlertNotificationModel).where(
            AlertNotificationModel.tenant_id == tenant_id, AlertNotificationModel.alert_id == alert_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
