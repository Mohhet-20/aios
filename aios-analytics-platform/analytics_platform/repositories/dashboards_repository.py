from __future__ import annotations

from sqlalchemy import select

from analytics_platform.models.dashboards import DashboardModel, DashboardWidgetModel, SavedViewModel
from analytics_platform.repositories.base import SQLAlchemyRepository


class DashboardRepository(SQLAlchemyRepository[DashboardModel]):
    model = DashboardModel

    async def list_for_tenant(self, tenant_id: str, *, status: str | None = None) -> list[DashboardModel]:
        stmt = select(DashboardModel).where(
            DashboardModel.tenant_id == tenant_id, DashboardModel.is_deleted.is_(False),
        )
        if status:
            stmt = stmt.where(DashboardModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())


class DashboardWidgetRepository(SQLAlchemyRepository[DashboardWidgetModel]):
    model = DashboardWidgetModel

    async def list_for_dashboard(self, tenant_id: str, dashboard_id: str) -> list[DashboardWidgetModel]:
        stmt = select(DashboardWidgetModel).where(
            DashboardWidgetModel.tenant_id == tenant_id, DashboardWidgetModel.dashboard_id == dashboard_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_dashboard(self, tenant_id: str, dashboard_id: str) -> int:
        return len(await self.list_for_dashboard(tenant_id, dashboard_id))


class SavedViewRepository(SQLAlchemyRepository[SavedViewModel]):
    model = SavedViewModel

    async def list_for_dashboard(self, tenant_id: str, dashboard_id: str) -> list[SavedViewModel]:
        stmt = select(SavedViewModel).where(
            SavedViewModel.tenant_id == tenant_id, SavedViewModel.dashboard_id == dashboard_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
