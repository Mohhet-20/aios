from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from observability_platform.models.governance import AccessGrantModel, AuditLogEntryModel, RetentionPolicyModel
from observability_platform.repositories.base import SQLAlchemyRepository


class AccessGrantRepository(SQLAlchemyRepository[AccessGrantModel]):
    model = AccessGrantModel

    async def list_for_principal(self, tenant_id: str, principal_id: str) -> list[AccessGrantModel]:
        stmt = select(AccessGrantModel).where(
            AccessGrantModel.tenant_id == tenant_id,
            AccessGrantModel.principal_id == principal_id,
            AccessGrantModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())


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

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(AuditLogEntryModel).where(
            AuditLogEntryModel.tenant_id == tenant_id, AuditLogEntryModel.occurred_at < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class RetentionPolicyRepository(SQLAlchemyRepository[RetentionPolicyModel]):
    model = RetentionPolicyModel

    async def get_for_resource(self, tenant_id: str, resource_type: str) -> RetentionPolicyModel | None:
        stmt = select(RetentionPolicyModel).where(
            RetentionPolicyModel.tenant_id == tenant_id, RetentionPolicyModel.resource_type == resource_type
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[RetentionPolicyModel]:
        stmt = select(RetentionPolicyModel).where(RetentionPolicyModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())
