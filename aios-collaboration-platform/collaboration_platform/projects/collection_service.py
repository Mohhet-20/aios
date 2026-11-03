"""CollectionService: user-curated groupings of assets (distinct from
folders — a folder is one asset's single location, a collection is a
many-to-many cross-cutting grouping, e.g. "Q3 launch assets" pulling
together prompts from three different folders)."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError
from collaboration_platform.models.workspace import CollectionItemModel, CollectionModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class CollectionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_collection(self, workspace_id: str, *, name: str, owner_id: str, description: str | None = None, is_public: bool = False) -> CollectionModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        return await self.repos.collections.add(
            CollectionModel(workspace_id=workspace_id, name=name, description=description, owner_id=owner_id, is_public=is_public)
        )

    async def add_item(self, collection_id: str, asset_id: str, *, added_by: str) -> CollectionItemModel:
        await self.repos.collections.get_or_404(collection_id)
        await self.repos.assets.get_or_404(asset_id)
        existing = await self.repos.collection_items.get_for_collection_and_asset(collection_id, asset_id)
        if existing is not None:
            raise ConflictError(f"asset '{asset_id}' is already in collection '{collection_id}'")
        from collaboration_platform.database.base import utcnow
        return await self.repos.collection_items.add(
            CollectionItemModel(collection_id=collection_id, asset_id=asset_id, added_by=added_by, added_at=utcnow())
        )

    async def remove_item(self, collection_id: str, asset_id: str) -> None:
        item = await self.repos.collection_items.get_for_collection_and_asset(collection_id, asset_id)
        if item is None:
            raise NotFoundError(f"asset '{asset_id}' is not in collection '{collection_id}'")
        await self.repos.collection_items.delete(item, hard=True)

    async def list_items(self, collection_id: str) -> list[CollectionItemModel]:
        return await self.repos.collection_items.list_for_collection(collection_id)

    async def list_for_workspace(self, workspace_id: str) -> list[CollectionModel]:
        return await self.repos.collections.list_for_workspace(workspace_id)
