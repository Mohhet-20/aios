from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.discovery import ToolFavoriteModel
from tool_platform.repositories.base import SQLAlchemyRepository


class ToolFavoriteRepository(SQLAlchemyRepository[ToolFavoriteModel]):
    model = ToolFavoriteModel

    async def list_for_user(self, user_id: str) -> list[ToolFavoriteModel]:
        stmt = select(ToolFavoriteModel).where(ToolFavoriteModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_favorite(self, tool_id: str, user_id: str) -> ToolFavoriteModel | None:
        stmt = select(ToolFavoriteModel).where(
            ToolFavoriteModel.tool_id == tool_id, ToolFavoriteModel.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalars().first()
