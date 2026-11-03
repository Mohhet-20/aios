from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.knowledge_base import KbArticleModel
from docs_platform.repositories.base import SQLAlchemyRepository


class KbArticleRepository(SQLAlchemyRepository[KbArticleModel]):
    model = KbArticleModel

    async def get_by_slug(self, tenant_id: str, slug: str) -> KbArticleModel | None:
        stmt = select(KbArticleModel).where(
            KbArticleModel.tenant_id == tenant_id, KbArticleModel.slug == slug, KbArticleModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, article_type: str | None = None, status: str | None = None) -> list[KbArticleModel]:
        stmt = select(KbArticleModel).where(KbArticleModel.tenant_id == tenant_id, KbArticleModel.is_deleted.is_(False))
        if article_type:
            stmt = stmt.where(KbArticleModel.article_type == article_type)
        if status:
            stmt = stmt.where(KbArticleModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())
