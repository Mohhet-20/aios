"""FavoriteService: per-user asset favorites (distinct from library
favorites — this is any asset, not just published library entries)."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError
from collaboration_platform.database.base import utcnow
from collaboration_platform.models.workspace import FavoriteModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class FavoriteService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_favorite(self, user_id: str, asset_id: str) -> FavoriteModel:
        await self.repos.assets.get_or_404(asset_id)
        existing = await self.repos.favorites.get_for_user_and_asset(user_id, asset_id)
        if existing is not None:
            raise ConflictError(f"asset '{asset_id}' is already favorited by '{user_id}'")
        return await self.repos.favorites.add(FavoriteModel(user_id=user_id, asset_id=asset_id, created_at=utcnow()))

    async def remove_favorite(self, user_id: str, asset_id: str) -> None:
        favorite = await self.repos.favorites.get_for_user_and_asset(user_id, asset_id)
        if favorite is None:
            raise NotFoundError(f"asset '{asset_id}' is not favorited by '{user_id}'")
        await self.repos.favorites.delete(favorite, hard=True)

    async def list_for_user(self, user_id: str) -> list[FavoriteModel]:
        return await self.repos.favorites.list_for_user(user_id)
