from __future__ import annotations

from sqlalchemy import select

from observability_platform.models.reporting import ReportModel
from observability_platform.repositories.base import SQLAlchemyRepository


class ReportRepository(SQLAlchemyRepository[ReportModel]):
    model = ReportModel

    async def list_for_tenant(self, tenant_id: str, *, report_type: str | None = None, limit: int = 100) -> list[ReportModel]:
        stmt = select(ReportModel).where(ReportModel.tenant_id == tenant_id)
        if report_type:
            stmt = stmt.where(ReportModel.report_type == report_type)
        stmt = stmt.order_by(ReportModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
