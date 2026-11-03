from __future__ import annotations

from sqlalchemy import desc, select

from collaboration_platform.models.governance import (
    AssetPermissionModel,
    AuditLogEntryModel,
    ExternalShareModel,
    RetentionPolicyModel,
    SharingLinkModel,
    WorkspacePermissionModel,
)
from collaboration_platform.repositories.base import SQLAlchemyRepository


class WorkspacePermissionRepository(SQLAlchemyRepository[WorkspacePermissionModel]):
    model = WorkspacePermissionModel

    async def list_for_workspace(self, workspace_id: str) -> list[WorkspacePermissionModel]:
        stmt = select(WorkspacePermissionModel).where(WorkspacePermissionModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_principal(self, workspace_id: str, principal_type: str, principal_id: str) -> WorkspacePermissionModel | None:
        stmt = select(WorkspacePermissionModel).where(
            WorkspacePermissionModel.workspace_id == workspace_id,
            WorkspacePermissionModel.principal_type == principal_type,
            WorkspacePermissionModel.principal_id == principal_id,
        )
        return (await self.session.execute(stmt)).scalars().first()


class AssetPermissionRepository(SQLAlchemyRepository[AssetPermissionModel]):
    model = AssetPermissionModel

    async def list_for_asset(self, asset_id: str) -> list[AssetPermissionModel]:
        stmt = select(AssetPermissionModel).where(AssetPermissionModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_principal(self, asset_id: str, principal_type: str, principal_id: str) -> AssetPermissionModel | None:
        stmt = select(AssetPermissionModel).where(
            AssetPermissionModel.asset_id == asset_id,
            AssetPermissionModel.principal_type == principal_type,
            AssetPermissionModel.principal_id == principal_id,
        )
        return (await self.session.execute(stmt)).scalars().first()


class SharingLinkRepository(SQLAlchemyRepository[SharingLinkModel]):
    model = SharingLinkModel

    async def get_by_token_hash(self, token_hash: str) -> SharingLinkModel | None:
        stmt = select(SharingLinkModel).where(SharingLinkModel.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_asset(self, asset_id: str) -> list[SharingLinkModel]:
        stmt = select(SharingLinkModel).where(SharingLinkModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())


class ExternalShareRepository(SQLAlchemyRepository[ExternalShareModel]):
    model = ExternalShareModel

    async def list_for_asset(self, asset_id: str) -> list[ExternalShareModel]:
        stmt = select(ExternalShareModel).where(ExternalShareModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_asset_and_email(self, asset_id: str, email: str) -> ExternalShareModel | None:
        stmt = select(ExternalShareModel).where(ExternalShareModel.asset_id == asset_id, ExternalShareModel.email == email)
        return (await self.session.execute(stmt)).scalars().first()


class AuditLogEntryRepository(SQLAlchemyRepository[AuditLogEntryModel]):
    model = AuditLogEntryModel

    async def list_for_workspace(self, workspace_id: str, *, action: str | None = None, limit: int = 200) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(AuditLogEntryModel.workspace_id == workspace_id)
        if action:
            stmt = stmt.where(AuditLogEntryModel.action == action)
        stmt = stmt.order_by(desc(AuditLogEntryModel.created_at)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_actor(self, actor_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(AuditLogEntryModel.actor_id == actor_id).order_by(desc(AuditLogEntryModel.created_at)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class RetentionPolicyRepository(SQLAlchemyRepository[RetentionPolicyModel]):
    model = RetentionPolicyModel

    async def list_for_workspace(self, workspace_id: str) -> list[RetentionPolicyModel]:
        stmt = select(RetentionPolicyModel).where(RetentionPolicyModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_workspace_and_type(self, workspace_id: str, resource_type: str) -> RetentionPolicyModel | None:
        stmt = select(RetentionPolicyModel).where(
            RetentionPolicyModel.workspace_id == workspace_id, RetentionPolicyModel.resource_type == resource_type
        )
        return (await self.session.execute(stmt)).scalars().first()
