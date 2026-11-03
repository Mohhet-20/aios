from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.collaboration import AuditLogEntryModel, CommentModel, ReviewModel
from docs_platform.repositories.base import SQLAlchemyRepository


class CommentRepository(SQLAlchemyRepository[CommentModel]):
    model = CommentModel

    async def list_for_target(self, tenant_id: str, target_ref: str) -> list[CommentModel]:
        stmt = select(CommentModel).where(
            CommentModel.tenant_id == tenant_id, CommentModel.target_ref == target_ref,
        ).order_by(CommentModel.created_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())


class ReviewRepository(SQLAlchemyRepository[ReviewModel]):
    model = ReviewModel

    async def list_for_page(self, tenant_id: str, page_id: str) -> list[ReviewModel]:
        stmt = select(ReviewModel).where(
            ReviewModel.tenant_id == tenant_id, ReviewModel.page_id == page_id,
        ).order_by(ReviewModel.requested_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class AuditLogEntryRepository(SQLAlchemyRepository[AuditLogEntryModel]):
    model = AuditLogEntryModel

    async def list_for_target(self, tenant_id: str, target_ref: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(
            AuditLogEntryModel.tenant_id == tenant_id, AuditLogEntryModel.target_ref == target_ref,
        ).order_by(AuditLogEntryModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_recent(self, tenant_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        stmt = select(AuditLogEntryModel).where(
            AuditLogEntryModel.tenant_id == tenant_id,
        ).order_by(AuditLogEntryModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
