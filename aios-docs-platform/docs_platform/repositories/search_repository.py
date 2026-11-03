from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.search import SearchQueryLogModel
from docs_platform.repositories.base import SQLAlchemyRepository


class SearchQueryLogRepository(SQLAlchemyRepository[SearchQueryLogModel]):
    model = SearchQueryLogModel

    async def list_recent(self, tenant_id: str, *, limit: int = 100) -> list[SearchQueryLogModel]:
        stmt = select(SearchQueryLogModel).where(
            SearchQueryLogModel.tenant_id == tenant_id,
        ).order_by(SearchQueryLogModel.searched_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_failed(self, tenant_id: str, *, limit: int = 100) -> list[SearchQueryLogModel]:
        stmt = select(SearchQueryLogModel).where(
            SearchQueryLogModel.tenant_id == tenant_id, SearchQueryLogModel.result_count == 0,
        ).order_by(SearchQueryLogModel.searched_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
