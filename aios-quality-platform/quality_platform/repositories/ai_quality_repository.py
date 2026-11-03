from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.ai_quality import AiQualityBaselineModel, AiQualityEvaluationModel, RegressionScanModel
from quality_platform.repositories.base import SQLAlchemyRepository


class AiQualityBaselineRepository(SQLAlchemyRepository[AiQualityBaselineModel]):
    model = AiQualityBaselineModel

    async def get_for_subject(self, tenant_id: str, dimension: str, subject_ref: str) -> AiQualityBaselineModel | None:
        stmt = select(AiQualityBaselineModel).where(
            AiQualityBaselineModel.tenant_id == tenant_id, AiQualityBaselineModel.dimension == dimension,
            AiQualityBaselineModel.subject_ref == subject_ref, AiQualityBaselineModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()


class AiQualityEvaluationRepository(SQLAlchemyRepository[AiQualityEvaluationModel]):
    model = AiQualityEvaluationModel

    async def list_for_subject(
        self, tenant_id: str, dimension: str, subject_ref: str, *, limit: int = 200,
    ) -> list[AiQualityEvaluationModel]:
        stmt = select(AiQualityEvaluationModel).where(
            AiQualityEvaluationModel.tenant_id == tenant_id, AiQualityEvaluationModel.dimension == dimension,
            AiQualityEvaluationModel.subject_ref == subject_ref,
        ).order_by(AiQualityEvaluationModel.evaluated_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class RegressionScanRepository(SQLAlchemyRepository[RegressionScanModel]):
    model = RegressionScanModel

    async def list_for_tenant(self, tenant_id: str, *, dimension: str | None = None, limit: int = 100) -> list[RegressionScanModel]:
        stmt = select(RegressionScanModel).where(RegressionScanModel.tenant_id == tenant_id)
        if dimension:
            stmt = stmt.where(RegressionScanModel.dimension == dimension)
        stmt = stmt.order_by(RegressionScanModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
