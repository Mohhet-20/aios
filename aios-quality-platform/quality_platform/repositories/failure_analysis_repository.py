from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.failure_analysis import FailurePatternModel, RiskAssessmentModel
from quality_platform.repositories.base import SQLAlchemyRepository


class FailurePatternRepository(SQLAlchemyRepository[FailurePatternModel]):
    model = FailurePatternModel

    async def get_for_subject(self, tenant_id: str, pattern_type: str, subject_ref: str) -> FailurePatternModel | None:
        stmt = select(FailurePatternModel).where(
            FailurePatternModel.tenant_id == tenant_id, FailurePatternModel.pattern_type == pattern_type,
            FailurePatternModel.subject_ref == subject_ref,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, pattern_type: str | None = None, min_occurrences: int = 1) -> list[FailurePatternModel]:
        stmt = select(FailurePatternModel).where(
            FailurePatternModel.tenant_id == tenant_id, FailurePatternModel.occurrences >= min_occurrences,
        )
        if pattern_type:
            stmt = stmt.where(FailurePatternModel.pattern_type == pattern_type)
        return list((await self.session.execute(stmt)).scalars().all())


class RiskAssessmentRepository(SQLAlchemyRepository[RiskAssessmentModel]):
    model = RiskAssessmentModel

    async def list_for_subject(self, tenant_id: str, subject_ref: str, *, limit: int = 50) -> list[RiskAssessmentModel]:
        stmt = select(RiskAssessmentModel).where(
            RiskAssessmentModel.tenant_id == tenant_id, RiskAssessmentModel.subject_ref == subject_ref,
        ).order_by(RiskAssessmentModel.assessed_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
