"""BookmarkService: personal asset bookmarks with an optional note —
distinct from `FavoriteService` in intent (a favorite is "I care about
this," a bookmark is "I'm coming back to this with a note attached"),
kept as separate services/tables so each can evolve its own semantics
independently."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError
from collaboration_platform.models.productivity import BookmarkModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class BookmarkService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_bookmark(self, user_id: str, asset_id: str, *, note: str | None = None) -> BookmarkModel:
        await self.repos.assets.get_or_404(asset_id)
        existing = await self.repos.bookmarks.get_for_user_and_asset(user_id, asset_id)
        if existing is not None:
            raise ConflictError(f"asset '{asset_id}' is already bookmarked by '{user_id}'")
        return await self.repos.bookmarks.add(BookmarkModel(user_id=user_id, asset_id=asset_id, note=note))

    async def remove_bookmark(self, user_id: str, asset_id: str) -> None:
        existing = await self.repos.bookmarks.get_for_user_and_asset(user_id, asset_id)
        if existing is None:
            raise NotFoundError(f"asset '{asset_id}' is not bookmarked by '{user_id}'")
        await self.repos.bookmarks.delete(existing, hard=True)

    async def list_for_user(self, user_id: str) -> list[BookmarkModel]:
        return await self.repos.bookmarks.list_for_user(user_id)
