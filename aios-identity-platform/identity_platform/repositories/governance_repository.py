from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.governance import AuditLogEntryModel
from identity_platform.repositories.base import SQLAlchemyRepository


class AuditLogEntryRepository(SQLAlchemyRepository[AuditLogEntryModel]):
    model = AuditLogEntryModel

    async def list_for_organization(self, organization_id: str, *, action: str | None = None, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(AuditLogEntryModel.organization_id == organization_id)
        if action:
            stmt = stmt.where(AuditLogEntryModel.action == action)
        stmt = stmt.order_by(AuditLogEntryModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_actor(self, actor_type: str, actor_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(
            AuditLogEntryModel.actor_type == actor_type, AuditLogEntryModel.actor_id == actor_id,
        ).order_by(AuditLogEntryModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_resource(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(
            AuditLogEntryModel.resource_type == resource_type, AuditLogEntryModel.resource_id == resource_id,
        ).order_by(AuditLogEntryModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
