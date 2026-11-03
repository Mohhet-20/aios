from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.analytics import AnalyticsEventModel, BrokenLinkModel, FeedbackModel
from docs_platform.repositories.base import SQLAlchemyRepository


class AnalyticsEventRepository(SQLAlchemyRepository[AnalyticsEventModel]):
    model = AnalyticsEventModel

    async def list_for_tenant(self, tenant_id: str, *, event_type: str | None = None, limit: int = 500) -> list[AnalyticsEventModel]:
        stmt = select(AnalyticsEventModel).where(AnalyticsEventModel.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(AnalyticsEventModel.event_type == event_type)
        stmt = stmt.order_by(AnalyticsEventModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class FeedbackRepository(SQLAlchemyRepository[FeedbackModel]):
    model = FeedbackModel

    async def list_for_subject(self, tenant_id: str, subject_ref: str, *, limit: int = 100) -> list[FeedbackModel]:
        stmt = select(FeedbackModel).where(
            FeedbackModel.tenant_id == tenant_id, FeedbackModel.subject_ref == subject_ref,
        ).order_by(FeedbackModel.submitted_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class BrokenLinkRepository(SQLAlchemyRepository[BrokenLinkModel]):
    model = BrokenLinkModel

    async def list_unresolved(self, tenant_id: str) -> list[BrokenLinkModel]:
        stmt = select(BrokenLinkModel).where(BrokenLinkModel.tenant_id == tenant_id, BrokenLinkModel.resolved.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())
