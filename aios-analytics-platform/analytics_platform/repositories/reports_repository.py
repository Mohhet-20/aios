from __future__ import annotations

from sqlalchemy import select

from analytics_platform.models.reports import ReportDefinitionModel, ReportRunModel
from analytics_platform.repositories.base import SQLAlchemyRepository


class ReportDefinitionRepository(SQLAlchemyRepository[ReportDefinitionModel]):
    model = ReportDefinitionModel

    async def list_for_tenant(self, tenant_id: str, *, report_type: str | None = None) -> list[ReportDefinitionModel]:
        stmt = select(ReportDefinitionModel).where(
            ReportDefinitionModel.tenant_id == tenant_id, ReportDefinitionModel.is_deleted.is_(False),
        )
        if report_type:
            stmt = stmt.where(ReportDefinitionModel.report_type == report_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_scheduled(self, tenant_id: str) -> list[ReportDefinitionModel]:
        stmt = select(ReportDefinitionModel).where(
            ReportDefinitionModel.tenant_id == tenant_id, ReportDefinitionModel.is_deleted.is_(False),
            ReportDefinitionModel.schedule != "none", ReportDefinitionModel.status == "active",
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ReportRunRepository(SQLAlchemyRepository[ReportRunModel]):
    model = ReportRunModel

    async def list_for_definition(self, tenant_id: str, report_definition_id: str, *, limit: int = 100) -> list[ReportRunModel]:
        stmt = select(ReportRunModel).where(
            ReportRunModel.tenant_id == tenant_id, ReportRunModel.report_definition_id == report_definition_id,
        ).order_by(ReportRunModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
