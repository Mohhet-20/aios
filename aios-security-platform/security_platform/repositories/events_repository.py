from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from security_platform.models.events import AuditLogEntryModel, SecurityEventModel
from security_platform.repositories.base import SQLAlchemyRepository


class SecurityEventRepository(SQLAlchemyRepository[SecurityEventModel]):
    model = SecurityEventModel

    async def list_recent(
        self, tenant_id: str, *, event_type: str | None = None, severity: str | None = None, limit: int = 200
    ) -> list[SecurityEventModel]:
        stmt = select(SecurityEventModel).where(SecurityEventModel.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(SecurityEventModel.event_type == event_type)
        if severity:
            stmt = stmt.where(SecurityEventModel.severity == severity)
        stmt = stmt.order_by(SecurityEventModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_type(self, tenant_id: str, *, start_time: datetime | None = None) -> dict[str, int]:
        from sqlalchemy import func

        stmt = select(SecurityEventModel.event_type, func.count()).where(SecurityEventModel.tenant_id == tenant_id)
        if start_time:
            stmt = stmt.where(SecurityEventModel.occurred_at >= start_time)
        stmt = stmt.group_by(SecurityEventModel.event_type)
        rows = (await self.session.execute(stmt)).all()
        return {t: count for t, count in rows}

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(SecurityEventModel).where(
            SecurityEventModel.tenant_id == tenant_id, SecurityEventModel.occurred_at < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class AuditLogEntryRepository(SQLAlchemyRepository[AuditLogEntryModel]):
    model = AuditLogEntryModel

    async def list_for_tenant(self, tenant_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        stmt = (
            select(AuditLogEntryModel)
            .where(AuditLogEntryModel.tenant_id == tenant_id)
            .order_by(AuditLogEntryModel.occurred_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_resource(self, tenant_id: str, resource_type: str, resource_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        stmt = (
            select(AuditLogEntryModel)
            .where(
                AuditLogEntryModel.tenant_id == tenant_id,
                AuditLogEntryModel.resource_type == resource_type,
                AuditLogEntryModel.resource_id == resource_id,
            )
            .order_by(AuditLogEntryModel.occurred_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_actor(self, tenant_id: str, actor_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        stmt = (
            select(AuditLogEntryModel)
            .where(AuditLogEntryModel.tenant_id == tenant_id, AuditLogEntryModel.actor_id == actor_id)
            .order_by(AuditLogEntryModel.occurred_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(AuditLogEntryModel).where(
            AuditLogEntryModel.tenant_id == tenant_id, AuditLogEntryModel.occurred_at < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
