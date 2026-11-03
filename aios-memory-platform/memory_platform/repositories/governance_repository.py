from __future__ import annotations

from sqlalchemy import select

from memory_platform.models.governance import AuditLogEntryModel, PermissionGrantModel, RetentionPolicyModel
from memory_platform.repositories.base import SQLAlchemyRepository


class PermissionGrantRepository(SQLAlchemyRepository[PermissionGrantModel]):
    model = PermissionGrantModel

    async def list_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        return await self.list(filters={"principal_id": principal_id})

    async def list_for_resource(self, resource_type: str, resource_id: str) -> list[PermissionGrantModel]:
        return await self.list(filters={"resource_type": resource_type, "resource_id": resource_id})


class RetentionPolicyRepository(SQLAlchemyRepository[RetentionPolicyModel]):
    model = RetentionPolicyModel

    async def list_active_for_workspace(self, workspace_id: str) -> list[RetentionPolicyModel]:
        stmt = select(RetentionPolicyModel).where(RetentionPolicyModel.workspace_id == workspace_id, RetentionPolicyModel.is_active.is_(True))
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
