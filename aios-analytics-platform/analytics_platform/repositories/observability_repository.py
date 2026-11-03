from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from analytics_platform.models.observability import (
    ForecastAccuracyModel,
    QueryPerformanceModel,
    RecommendationOutcomeModel,
    UsageEventModel,
)
from analytics_platform.repositories.base import SQLAlchemyRepository


class UsageEventRepository(SQLAlchemyRepository[UsageEventModel]):
    model = UsageEventModel

    async def list_recent(self, tenant_id: str, *, event_type: str | None = None, limit: int = 500) -> list[UsageEventModel]:
        stmt = select(UsageEventModel).where(UsageEventModel.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(UsageEventModel.event_type == event_type)
        stmt = stmt.order_by(UsageEventModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        from sqlalchemy import delete

        stmt = delete(UsageEventModel).where(
            UsageEventModel.tenant_id == tenant_id, UsageEventModel.occurred_at < cutoff,
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class QueryPerformanceRepository(SQLAlchemyRepository[QueryPerformanceModel]):
    model = QueryPerformanceModel

    async def list_recent(self, tenant_id: str, *, limit: int = 500) -> list[QueryPerformanceModel]:
        stmt = select(QueryPerformanceModel).where(
            QueryPerformanceModel.tenant_id == tenant_id,
        ).order_by(QueryPerformanceModel.executed_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class ForecastAccuracyRepository(SQLAlchemyRepository[ForecastAccuracyModel]):
    model = ForecastAccuracyModel

    async def list_for_job(self, tenant_id: str, forecast_job_id: str) -> list[ForecastAccuracyModel]:
        stmt = select(ForecastAccuracyModel).where(
            ForecastAccuracyModel.tenant_id == tenant_id, ForecastAccuracyModel.forecast_job_id == forecast_job_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class RecommendationOutcomeRepository(SQLAlchemyRepository[RecommendationOutcomeModel]):
    model = RecommendationOutcomeModel

    async def list_for_recommendation(self, tenant_id: str, recommendation_id: str) -> list[RecommendationOutcomeModel]:
        stmt = select(RecommendationOutcomeModel).where(
            RecommendationOutcomeModel.tenant_id == tenant_id, RecommendationOutcomeModel.recommendation_id == recommendation_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_recent(self, tenant_id: str, *, limit: int = 500) -> list[RecommendationOutcomeModel]:
        stmt = select(RecommendationOutcomeModel).where(
            RecommendationOutcomeModel.tenant_id == tenant_id,
        ).order_by(RecommendationOutcomeModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
