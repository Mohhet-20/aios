"""PinnedItemService: per-user, per-workspace pinned assets for quick
access, with an explicit `position` for drag-to-reorder UIs."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError
from collaboration_platform.models.productivity import PinnedItemModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class PinnedItemService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def pin(self, user_id: str, workspace_id: str, asset_id: str) -> PinnedItemModel:
        await self.repos.assets.get_or_404(asset_id)
        existing = [p for p in await self.repos.pinned_items.list_for_user_and_workspace(user_id, workspace_id) if p.asset_id == asset_id]
        if existing:
            raise ConflictError(f"asset '{asset_id}' is already pinned by '{user_id}' in workspace '{workspace_id}'")
        current = await self.repos.pinned_items.list_for_user_and_workspace(user_id, workspace_id)
        return await self.repos.pinned_items.add(
            PinnedItemModel(user_id=user_id, workspace_id=workspace_id, asset_id=asset_id, position=len(current))
        )

    async def unpin(self, pinned_item_id: str) -> None:
        item = await self.repos.pinned_items.get(pinned_item_id)
        if item is None:
            raise NotFoundError(f"pinned item '{pinned_item_id}' not found")
        await self.repos.pinned_items.delete(item, hard=True)

    async def reorder(self, user_id: str, workspace_id: str, ordered_asset_ids: list[str]) -> list[PinnedItemModel]:
        items = await self.repos.pinned_items.list_for_user_and_workspace(user_id, workspace_id)
        by_asset = {i.asset_id: i for i in items}
        updated = []
        for position, asset_id in enumerate(ordered_asset_ids):
            item = by_asset.get(asset_id)
            if item is not None:
                item.position = position
                updated.append(await self.repos.pinned_items.update(item))
        return updated

    async def list_for_user_and_workspace(self, user_id: str, workspace_id: str) -> list[PinnedItemModel]:
        return await self.repos.pinned_items.list_for_user_and_workspace(user_id, workspace_id)
