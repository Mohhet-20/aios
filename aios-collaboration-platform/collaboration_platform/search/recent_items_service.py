"""RecentItemsService: per-user "recently viewed" LRU list, capped at
`recent_items_per_user_limit`. Trimming happens on write (after
recording a view, delete anything past the limit) rather than only at
read time, so the table itself never grows unbounded per user."""
from __future__ import annotations

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.database.base import utcnow
from collaboration_platform.models.search import RecentItemModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class RecentItemsService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def track_view(self, user_id: str, asset_id: str) -> RecentItemModel:
        await self.repos.assets.get_or_404(asset_id)
        existing = await self.repos.recent_items.get_for_user_and_asset(user_id, asset_id)
        if existing is not None:
            existing.viewed_at = utcnow()
            item = await self.repos.recent_items.update(existing)
        else:
            item = await self.repos.recent_items.add(RecentItemModel(user_id=user_id, asset_id=asset_id))

        all_items = await self.repos.recent_items.list_for_user(user_id, limit=10_000)
        overflow = all_items[self.settings.recent_items_per_user_limit:]
        for stale in overflow:
            await self.repos.recent_items.delete(stale, hard=True)
        return item

    async def list_recent(self, user_id: str) -> list[RecentItemModel]:
        return await self.repos.recent_items.list_for_user(user_id, limit=self.settings.recent_items_per_user_limit)
