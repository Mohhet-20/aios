from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.governance import AuditLogEntryModel, PromptPermissionGrantModel
from prompt_platform.repositories.base import SQLAlchemyRepository


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


class PromptPermissionGrantRepository(SQLAlchemyRepository[PromptPermissionGrantModel]):
    model = PromptPermissionGrantModel

    async def list_for_principal(self, principal_id: str) -> list[PromptPermissionGrantModel]:
        stmt = select(PromptPermissionGrantModel).where(PromptPermissionGrantModel.principal_id == principal_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_resource(self, resource_type: str, resource_id: str) -> list[PromptPermissionGrantModel]:
        stmt = select(PromptPermissionGrantModel).where(
            PromptPermissionGrantModel.resource_type == resource_type, PromptPermissionGrantModel.resource_id == resource_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
