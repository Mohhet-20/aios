from __future__ import annotations

from sqlalchemy import select

from analytics_platform.models.forecasts import ForecastJobModel
from analytics_platform.repositories.base import SQLAlchemyRepository


class ForecastJobRepository(SQLAlchemyRepository[ForecastJobModel]):
    model = ForecastJobModel

    async def list_for_tenant(self, tenant_id: str, *, forecast_type: str | None = None) -> list[ForecastJobModel]:
        stmt = select(ForecastJobModel).where(
            ForecastJobModel.tenant_id == tenant_id, ForecastJobModel.is_deleted.is_(False),
        )
        if forecast_type:
            stmt = stmt.where(ForecastJobModel.forecast_type == forecast_type)
        return list((await self.session.execute(stmt)).scalars().all())
