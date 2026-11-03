from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.governance import ApprovalGateModel, AuditLogEntryModel, PermissionGrantModel
from tool_platform.repositories.base import SQLAlchemyRepository


class PermissionGrantRepository(SQLAlchemyRepository[PermissionGrantModel]):
    model = PermissionGrantModel

    async def list_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        stmt = select(PermissionGrantModel).where(PermissionGrantModel.principal_id == principal_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_resource(self, principal_id: str, resource_type: str, resource_id: str) -> PermissionGrantModel | None:
        stmt = select(PermissionGrantModel).where(
            PermissionGrantModel.principal_id == principal_id,
            PermissionGrantModel.resource_type == resource_type,
            PermissionGrantModel.resource_id == resource_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_resource(self, resource_type: str, resource_id: str) -> list[PermissionGrantModel]:
        stmt = select(PermissionGrantModel).where(
            PermissionGrantModel.resource_type == resource_type, PermissionGrantModel.resource_id == resource_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ApprovalGateRepository(SQLAlchemyRepository[ApprovalGateModel]):
    model = ApprovalGateModel

    async def list_pending(self, *, resource_type: str | None = None) -> list[ApprovalGateModel]:
        stmt = select(ApprovalGateModel).where(ApprovalGateModel.status == "pending")
        if resource_type:
            stmt = stmt.where(ApprovalGateModel.resource_type == resource_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_resource(self, resource_type: str, resource_id: str) -> list[ApprovalGateModel]:
        stmt = select(ApprovalGateModel).where(
            ApprovalGateModel.resource_type == resource_type, ApprovalGateModel.resource_id == resource_id
        ).order_by(ApprovalGateModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class AuditLogEntryRepository(SQLAlchemyRepository[AuditLogEntryModel]):
    model = AuditLogEntryModel

    async def list_for_resource(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(
            AuditLogEntryModel.resource_type == resource_type, AuditLogEntryModel.resource_id == resource_id
        ).order_by(AuditLogEntryModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_actor(self, actor_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(AuditLogEntryModel.actor_id == actor_id).order_by(
            AuditLogEntryModel.created_at.desc()
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
