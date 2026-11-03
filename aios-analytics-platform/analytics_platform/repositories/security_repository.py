from __future__ import annotations

from sqlalchemy import select

from analytics_platform.models.security import (
    AnalyticsRoleGrantModel,
    AuditLogEntryModel,
    ColumnLevelSecurityRuleModel,
    DataLineageEdgeModel,
    RowLevelSecurityRuleModel,
)
from analytics_platform.repositories.base import SQLAlchemyRepository


class AnalyticsRoleGrantRepository(SQLAlchemyRepository[AnalyticsRoleGrantModel]):
    model = AnalyticsRoleGrantModel

    async def get_for_principal(self, tenant_id: str, principal_id: str, *, scope: str | None = None) -> AnalyticsRoleGrantModel | None:
        stmt = select(AnalyticsRoleGrantModel).where(
            AnalyticsRoleGrantModel.tenant_id == tenant_id, AnalyticsRoleGrantModel.principal_id == principal_id,
            AnalyticsRoleGrantModel.scope == scope,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[AnalyticsRoleGrantModel]:
        stmt = select(AnalyticsRoleGrantModel).where(AnalyticsRoleGrantModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())


class RowLevelSecurityRuleRepository(SQLAlchemyRepository[RowLevelSecurityRuleModel]):
    model = RowLevelSecurityRuleModel

    async def get_for_resource(self, tenant_id: str, resource_type: str) -> RowLevelSecurityRuleModel | None:
        stmt = select(RowLevelSecurityRuleModel).where(
            RowLevelSecurityRuleModel.tenant_id == tenant_id, RowLevelSecurityRuleModel.resource_type == resource_type,
        )
        return (await self.session.execute(stmt)).scalars().first()


class ColumnLevelSecurityRuleRepository(SQLAlchemyRepository[ColumnLevelSecurityRuleModel]):
    model = ColumnLevelSecurityRuleModel

    async def get_for_resource(self, tenant_id: str, resource_type: str) -> ColumnLevelSecurityRuleModel | None:
        stmt = select(ColumnLevelSecurityRuleModel).where(
            ColumnLevelSecurityRuleModel.tenant_id == tenant_id, ColumnLevelSecurityRuleModel.resource_type == resource_type,
        )
        return (await self.session.execute(stmt)).scalars().first()


class AuditLogEntryRepository(SQLAlchemyRepository[AuditLogEntryModel]):
    model = AuditLogEntryModel

    async def list_recent(self, tenant_id: str, *, action_type: str | None = None, limit: int = 200) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(AuditLogEntryModel.tenant_id == tenant_id)
        if action_type:
            stmt = stmt.where(AuditLogEntryModel.action_type == action_type)
        stmt = stmt.order_by(AuditLogEntryModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class DataLineageEdgeRepository(SQLAlchemyRepository[DataLineageEdgeModel]):
    model = DataLineageEdgeModel

    async def list_upstream(self, tenant_id: str, target_ref: str) -> list[DataLineageEdgeModel]:
        stmt = select(DataLineageEdgeModel).where(
            DataLineageEdgeModel.tenant_id == tenant_id, DataLineageEdgeModel.target_ref == target_ref,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_downstream(self, tenant_id: str, source_ref: str) -> list[DataLineageEdgeModel]:
        stmt = select(DataLineageEdgeModel).where(
            DataLineageEdgeModel.tenant_id == tenant_id, DataLineageEdgeModel.source_ref == source_ref,
        )
        return list((await self.session.execute(stmt)).scalars().all())
