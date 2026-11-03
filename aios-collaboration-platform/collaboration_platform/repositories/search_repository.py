from __future__ import annotations

from sqlalchemy import desc, select

from collaboration_platform.models.search import RecentItemModel, SavedSearchModel
from collaboration_platform.repositories.base import SQLAlchemyRepository


class SavedSearchRepository(SQLAlchemyRepository[SavedSearchModel]):
    model = SavedSearchModel

    async def list_for_user(self, user_id: str) -> list[SavedSearchModel]:
        stmt = select(SavedSearchModel).where(SavedSearchModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())


class RecentItemRepository(SQLAlchemyRepository[RecentItemModel]):
    model = RecentItemModel

    async def list_for_user(self, user_id: str, *, limit: int = 50) -> list[RecentItemModel]:
        stmt = (
            select(RecentItemModel)
            .where(RecentItemModel.user_id == user_id)
            .order_by(desc(RecentItemModel.viewed_at))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_user_and_asset(self, user_id: str, asset_id: str) -> RecentItemModel | None:
        stmt = select(RecentItemModel).where(RecentItemModel.user_id == user_id, RecentItemModel.asset_id == asset_id)
        return (await self.session.execute(stmt)).scalars().first()
