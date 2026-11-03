"""LibraryService: publishing an asset for reuse (prompt/agent/
workflow-template/tool-template/knowledge-template), install tracking,
and per-user library favorites. `install_count` is bumped via a single
atomic UPDATE (see `LibraryAssetRepository.increment_install_count`)
rather than a read-then-write, so concurrent installs can't undercount
— the same class of fix the Identity Platform needed for seat quotas,
applied preemptively here rather than discovered via a stress test,
since a simple counter increment is a well-known race shape."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError
from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import LibraryVisibility
from collaboration_platform.models.library import LibraryAssetModel, LibraryFavoriteModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class LibraryService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def publish(
        self, asset_id: str, *, library_type: str, published_by: str, visibility: LibraryVisibility = LibraryVisibility.PRIVATE
    ) -> LibraryAssetModel:
        await self.repos.assets.get_or_404(asset_id)
        if await self.repos.library_assets.get_for_asset(asset_id) is not None:
            raise ConflictError(f"asset '{asset_id}' is already published to the library")
        return await self.repos.library_assets.add(LibraryAssetModel(
            asset_id=asset_id, library_type=library_type, visibility=visibility.value, published_by=published_by,
        ))

    async def unpublish(self, library_asset_id: str) -> LibraryAssetModel:
        entry = await self.repos.library_assets.get_or_404(library_asset_id)
        entry.unpublished_at = utcnow()
        return await self.repos.library_assets.update(entry)

    async def update_visibility(self, library_asset_id: str, visibility: LibraryVisibility) -> LibraryAssetModel:
        entry = await self.repos.library_assets.get_or_404(library_asset_id)
        entry.visibility = visibility.value
        return await self.repos.library_assets.update(entry)

    async def record_install(self, library_asset_id: str) -> LibraryAssetModel:
        await self.repos.library_assets.get_or_404(library_asset_id)
        await self.repos.library_assets.increment_install_count(library_asset_id)
        return await self.repos.library_assets.get_or_404(library_asset_id)

    async def favorite(self, user_id: str, library_asset_id: str) -> LibraryFavoriteModel:
        await self.repos.library_assets.get_or_404(library_asset_id)
        existing = await self.repos.library_favorites.get_for_user_and_library_asset(user_id, library_asset_id)
        if existing is not None:
            raise ConflictError(f"user '{user_id}' already favorited library asset '{library_asset_id}'")
        return await self.repos.library_favorites.add(LibraryFavoriteModel(user_id=user_id, library_asset_id=library_asset_id))

    async def unfavorite(self, user_id: str, library_asset_id: str) -> None:
        existing = await self.repos.library_favorites.get_for_user_and_library_asset(user_id, library_asset_id)
        if existing is None:
            raise NotFoundError(f"user '{user_id}' has not favorited library asset '{library_asset_id}'")
        await self.repos.library_favorites.delete(existing, hard=True)

    async def list_published(self, *, visibility: LibraryVisibility | None = None, library_type: str | None = None) -> list[LibraryAssetModel]:
        return await self.repos.library_assets.list_published(
            visibility=visibility.value if visibility else None, library_type=library_type
        )

    async def list_favorites_for_user(self, user_id: str) -> list[LibraryFavoriteModel]:
        return await self.repos.library_favorites.list_for_user(user_id)
