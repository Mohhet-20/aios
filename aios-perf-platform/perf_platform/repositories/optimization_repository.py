from __future__ import annotations

from sqlalchemy import select

from perf_platform.models.optimization import RecommendationModel
from perf_platform.repositories.base import SQLAlchemyRepository


class RecommendationRepository(SQLAlchemyRepository[RecommendationModel]):
    model = RecommendationModel

    async def list_for_tenant(self, tenant_id: str, *, status: str | None = None, category: str | None = None) -> list[RecommendationModel]:
        stmt = select(RecommendationModel).where(RecommendationModel.tenant_id == tenant_id, RecommendationModel.is_deleted.is_(False))
        if status:
            stmt = stmt.where(RecommendationModel.status == status)
        if category:
            stmt = stmt.where(RecommendationModel.category == category)
        return list((await self.session.execute(stmt)).scalars().all())
