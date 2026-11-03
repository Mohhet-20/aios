from __future__ import annotations

from sqlalchemy import select

from eval_platform.models.analytics import AnalyticsSnapshotModel, RecommendationModel
from eval_platform.repositories.base import SQLAlchemyRepository


class AnalyticsSnapshotRepository(SQLAlchemyRepository[AnalyticsSnapshotModel]):
    model = AnalyticsSnapshotModel

    async def list_for_workspace(self, workspace_id: str, *, snapshot_type: str | None = None, limit: int = 100) -> list[AnalyticsSnapshotModel]:
        stmt = select(AnalyticsSnapshotModel).where(AnalyticsSnapshotModel.workspace_id == workspace_id)
        if snapshot_type:
            stmt = stmt.where(AnalyticsSnapshotModel.snapshot_type == snapshot_type)
        stmt = stmt.order_by(AnalyticsSnapshotModel.period_start.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class RecommendationRepository(SQLAlchemyRepository[RecommendationModel]):
    model = RecommendationModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, category: str | None = None) -> list[RecommendationModel]:
        stmt = select(RecommendationModel).where(RecommendationModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(RecommendationModel.status == status)
        if category:
            stmt = stmt.where(RecommendationModel.category == category)
        stmt = stmt.order_by(RecommendationModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
