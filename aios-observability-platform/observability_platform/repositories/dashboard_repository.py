from __future__ import annotations

from sqlalchemy import select

from observability_platform.models.dashboards import DashboardModel
from observability_platform.repositories.base import SQLAlchemyRepository


class DashboardRepository(SQLAlchemyRepository[DashboardModel]):
    model = DashboardModel

    async def list_for_tenant(self, tenant_id: str, *, dashboard_type: str | None = None) -> list[DashboardModel]:
        stmt = select(DashboardModel).where(DashboardModel.tenant_id == tenant_id, DashboardModel.is_deleted.is_(False))
        if dashboard_type:
            stmt = stmt.where(DashboardModel.dashboard_type == dashboard_type)
        return list((await self.session.execute(stmt)).scalars().all())
