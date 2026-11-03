from __future__ import annotations

from sqlalchemy import select

from agent_platform.models.governance import ApprovalGateModel, AuditLogEntryModel, PermissionGrantModel
from agent_platform.repositories.base import SQLAlchemyRepository


class ApprovalGateRepository(SQLAlchemyRepository[ApprovalGateModel]):
    model = ApprovalGateModel

    async def list_pending(self, *, limit: int = 100) -> list[ApprovalGateModel]:
        stmt = select(ApprovalGateModel).where(ApprovalGateModel.status == "pending").order_by(ApprovalGateModel.requested_at).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_task(self, task_id: str) -> list[ApprovalGateModel]:
        stmt = select(ApprovalGateModel).where(ApprovalGateModel.task_id == task_id)
        return list((await self.session.execute(stmt)).scalars().all())


class AuditLogEntryRepository(SQLAlchemyRepository[AuditLogEntryModel]):
    model = AuditLogEntryModel

    async def list_for_resource(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = (
            select(AuditLogEntryModel)
            .where(AuditLogEntryModel.resource_type == resource_type, AuditLogEntryModel.resource_id == resource_id)
            .order_by(AuditLogEntryModel.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PermissionGrantRepository(SQLAlchemyRepository[PermissionGrantModel]):
    model = PermissionGrantModel

    async def list_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        stmt = select(PermissionGrantModel).where(PermissionGrantModel.principal_id == principal_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_resource(self, resource_type: str, resource_id: str) -> list[PermissionGrantModel]:
        stmt = select(PermissionGrantModel).where(
            PermissionGrantModel.resource_type == resource_type, PermissionGrantModel.resource_id == resource_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
